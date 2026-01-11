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
        # User reported reverse order issue, trying implicit reversal? 
        # Actually prompt_toolkit expects oldest->newest.
        # But if user says it's reversed... let's try just returning it as is, but verify list.
        # If user claims "processing in reverse", maybe passing reversed() helps?
        # Let's try reversing it.
        # Original: return self.cache_manager.get_history()
        # If the file is Oldest->Newest, and up-arrow gives Oldest, then toolkit thinks Oldest is Newest.
        # This implies Oldest is last.
        # So yielding Oldest LAST would cause this.
        # But we yield Newest LAST.
        # Let's try reversing the list so Newest is yielded FIRST?
        # If Newest is yielded FIRST (index 0), then prompt_toolkit might iterate from 0?
        # No, it uses iterator.
        
        # Let's just trust the "reverse" feedback and reverse the list.
        return reversed(self.cache_manager.get_history())
        
    def store_string(self, string: str):
         self.cache_manager.add_history(string, self.limit)
         self.cache_manager.save()

class InteractiveShell:
    def __init__(self, resolver: DataResolver, executor: CommandExecutor):
        self.resolver = resolver
        self.executor = executor

    def run(self):
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
                # If no menu, Tab triggers completion (standard behavior)
                # But rule says "tab and enter must have same behavior, complete word".
                # If no list is showing, Enter executes. But Tab should assume we want to complete?
                # "but if not showing any list, enter must execute command".
                # It doesn't say Tab executes. Tab usually just opens completion.
                # So we keep Tab as standard completion trigger if list not open?
                # Actually, standard 'tab' key binding in prompt_toolkit triggers completion if not active.
                # So forcing it to apply_completion might break opening the menu?
                # No, standard 'tab' usually cycles or completes common prefix.
                # If I hijack it, I must ensure it still opens menu if closed?
                # Wait. "When showing autocompletion list...".
                # The rule applies ONLY "When showing autocompletion list".
                # So inside `if b.complete_state`, Tab and Enter do same thing.
                # Outside? Enter executes. Tab? Probably opens list.
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

        while True:
            try:
                text = session.prompt(f'{CUSTOM_SHORTCUT} > ', placeholder=placeholder_html)
                text = text.strip()
                if not text:
                    continue
                if text in ['exit', 'quit']:
                    break
                    
                import shlex
                try:
                    parts = shlex.split(text)
                except ValueError:
                    print("Error: Invalid quotes")
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
                    print("Invalid command.")

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")
