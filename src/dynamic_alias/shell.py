import sys
import os
import signal
from prompt_toolkit import PromptSession
from prompt_toolkit.history import History
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from .resolver import DataResolver
from .executor import CommandExecutor
from .completer import DynamicAliasCompleter
from .constants import CUSTOM_SHORTCUT

class CacheHistory(History):
    def __init__(self, cache_manager, limit: int = 20):
        super().__init__()
        self.cache_manager = cache_manager
        self.limit = limit
        
    def load_history_strings(self):
        # Return history in chronological order (oldest to newest)
        return reversed(self.cache_manager.get_history())
        
    def store_string(self, string: str):
         # Rule 1.2.25/1.2.26: 
         # We typically verify/save here, but PromptSession runs this in a background thread.
         # This causes a race condition with subprocesses (like set-local) that modify the cache concurrently.
         # To fix this, we disable saving here and manually handle it in the main loop (synchronously).
         pass

import json

class InteractiveShell:
    def __init__(self, resolver: DataResolver, executor: CommandExecutor):
        self.resolver = resolver
        self.executor = executor
        # Management flags supported in interactive mode
        self._management_flags = {
            f"--{CUSTOM_SHORTCUT}-clear-cache": self._cmd_clear_cache,
            f"--{CUSTOM_SHORTCUT}-clear-history": self._cmd_clear_history,
            f"--{CUSTOM_SHORTCUT}-clear-all": self._cmd_clear_all,
            f"--{CUSTOM_SHORTCUT}-clear-locals": self._cmd_clear_locals,
            f"--{CUSTOM_SHORTCUT}-set-locals": self._cmd_set_locals,
            f"--{CUSTOM_SHORTCUT}-dump": self._cmd_dump,
        }
        # Flags that are NOT supported in interactive mode
        self._unsupported_flags = {
            f"--{CUSTOM_SHORTCUT}-config",
            f"--{CUSTOM_SHORTCUT}-cache",
        }
    
    def _handle_interactive_management(self, parts: list) -> bool:
        """
        Handle management flags in interactive mode.
        Returns True if a management command was handled, False otherwise.
        """
        if not parts:
            return False
        
        flag = parts[0]
        
        # Check for unsupported flags
        if flag in self._unsupported_flags:
            print(f"Error: {flag} is not supported in interactive mode.")
            print("  Hint: Use this flag when starting from command line, e.g.:")
            print(f"    {CUSTOM_SHORTCUT} {flag} <path>")
            return True
        
        # Check for management flags
        if flag in self._management_flags:
            handler = self._management_flags[flag]
            handler(parts[1:])
            return True
        
        return False
    def _get_output(self):
        """Get the output strategy for current verbosity level."""
        from .output import get_output_strategy
        return get_output_strategy(self.resolver.config.global_config.verbosity)
    
    def _cmd_clear_cache(self, args: list):
        """Clear dynamic dict cache (keeps history)."""
        count = self.resolver.cache.clear_cache()
        self._get_output().verbose_log(f"[VERBOSE] Cache modified: cleared {count} dynamic dict entries")
        print(f"Cleared {count} cache entries (history preserved)")
    
    def _cmd_clear_history(self, args: list):
        """Clear command history."""
        if self.resolver.cache.clear_history():
            print("Command history cleared")
        else:
            print("No history to clear")
    
    def _cmd_clear_all(self, args: list):
        """Delete entire cache file."""
        if self.resolver.cache.delete_all():
            self._get_output().verbose_log(f"[VERBOSE] Cache file deleted: {self.resolver.cache.cache_file}")
            print(f"Cache file deleted: {self.resolver.cache.cache_file}")
        else:
            print(f"Cache file not found: {self.resolver.cache.cache_file}")
    
    def _cmd_clear_locals(self, args: list):
        """Clear all local variables."""
        if self.resolver.cache.clear_locals():
            self._get_output().verbose_log("[VERBOSE] Cache modified: cleared all _locals")
            print("Local variables cleared")
        else:
            print("No local variables to clear")
    
    def _cmd_set_locals(self, args: list):
        """Set a local variable."""
        if len(args) < 2:
            print(f"Error: --{CUSTOM_SHORTCUT}-set-locals requires <key> <value>")
            return
        key, value = args[0], args[1]
        self.resolver.cache.set_local(key, value)
        self._get_output().verbose_log(f"[VERBOSE] Cache modified: set _locals.{key} = '{value}'")
        print(f"Local variable set: {key}={value}")
    
    def _cmd_dump(self, args: list):
        """Print decrypted cache as JSON."""
        print(json.dumps(self.resolver.cache.cache, indent=2, ensure_ascii=False))

    def run(self):
        # Register SIGTERM handler for graceful cleanup when killed
        def cleanup_and_exit(signum, frame):
            if sys.platform != 'win32':
                os.system('stty sane 2>/dev/null')
            sys.exit(0)
        
        if sys.platform != 'win32':
            signal.signal(signal.SIGTERM, cleanup_and_exit)
            signal.signal(signal.SIGHUP, cleanup_and_exit)  # Also handle terminal close
        
        completer = DynamicAliasCompleter(self.resolver, self.executor)
        
        # Rule 1.1.10: Use styles from config (with defaults in models.py)
        global_config = self.resolver.config.global_config
        style = Style.from_dict(global_config.styles)
        
        # Placeholder styling
        placeholder_color = global_config.placeholder_color
        placeholder_text_content = global_config.placeholder_text
        placeholder_html = HTML(f'<style color="{placeholder_color}">{placeholder_text_content}</style>')

        bindings = KeyBindings()

        @bindings.add('enter')
        def _(event):
            b = event.current_buffer
            if b.complete_state:
                # If menu is open, Enter selects the item (autocompletes)
                if b.complete_state.current_completion:
                    b.apply_completion(b.complete_state.current_completion)
                elif b.complete_state.completions:
                    b.apply_completion(b.complete_state.completions[0])
            else:
                # If no menu, Enter executes
                b.validate_and_handle()

        @bindings.add('tab')
        def _(event):
            b = event.current_buffer
            if b.complete_state:
                # If menu is open, Tab selects the item (autocompletes) - SAME as Enter behavior for list
                if b.complete_state.current_completion:
                     b.apply_completion(b.complete_state.current_completion)
                elif b.complete_state.completions:
                     b.apply_completion(b.complete_state.completions[0])
            else:
                pass 
                
            # If we don't handle it here (i.e. not in complete_state), we should let default handling happen?
            # But KeyBinding catches it. We must manually trigger completion if not open.
            if not b.complete_state:
                b.start_completion(select_first=True)

        @bindings.add('backspace')
        def _(event):
            b = event.current_buffer
            
            # 1. Perform standard backspace
            doc = b.document
            if doc.cursor_position > 0:
                 b.delete_before_cursor(1)
            else:
                 # Nothing to delete
                 return

            # 2. Rule 1.2.13 & 1.2.15: Evaluate autocompletion again
            # We explicitly trigger completion after deletion to ensure menu updates immediately
            # even if we deleted the entire word or are now at an empty string.
            b.start_completion(select_first=False) # select_first=False to just show menu without pre-selecting to avoid aggressive intrusion
        
        history_size = global_config.history_size
        history = CacheHistory(self.resolver.cache, history_size)
        
        session = PromptSession(
            completer=completer,
            style=style,
            history=history,
            complete_while_typing=True,
            key_bindings=bindings
        )

        try:
            while True:
                try:
                    text = session.prompt(f'{CUSTOM_SHORTCUT} > ', placeholder=placeholder_html)
                    text = text.strip()
                    if not text:
                        continue
                    
                    # Manual History Management (Sync Logic)
                    # 1. Reload cache to pick up any changes from previous commands/subprocesses
                    self.resolver.cache.load()
                    # 2. Add current command to history
                    self.resolver.cache.add_history(text, global_config.history_size)
                    # 3. Save updated state (merging external changes + new history)
                    self.resolver.cache.save()

                    if text in ['exit', 'quit']:
                        break
                    
                    import shlex
                    try:
                        parts = shlex.split(text)
                    except ValueError:
                        print("Error: Invalid quotes")
                        continue
                    
                    # Handle management flags in interactive mode
                    # Note: config/cache path flags are NOT supported in interactive mode
                    if self._handle_interactive_management(parts):
                        continue
                        
                    result = self.executor.find_command(parts)
                    
                    if result:
                        cmd, vars, is_help, remaining = result
                        if is_help:
                            self.executor.print_help(cmd)
                        else:
                            self.executor.execute(cmd, vars, remaining)
                    
                    elif len(parts) == 1 and parts[0] in ('-h', '--help'):
                        self.executor.print_global_help()
                        
                    else:
                        # Shell mode: execute unrecognized commands directly in shell
                        if global_config.shell:
                            import subprocess
                            try:
                                if global_config.verbose:
                                    print(f"[VERBOSE] Shell mode: executing '{text}'")
                                subprocess.run(text, shell=True)
                            except Exception as shell_err:
                                print(f"Shell error: {shell_err}")
                        else:
                            print("Invalid command.")

                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break
                except Exception as e:
                    print(f"Error: {e}")
        finally:
            # Reset terminal state on exit (fixes bash invisible input issue)
            # Issue: prompt_toolkit can leave terminal in raw/alternate state
            if sys.platform != 'win32':
                os.system('stty sane 2>/dev/null')
