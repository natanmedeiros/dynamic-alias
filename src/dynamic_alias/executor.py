from __future__ import annotations

import re
import subprocess
import shlex
import json  # Rule 4.21
import sys
import os
import signal
from typing import Dict, List, Any, Optional, Union
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from .models import CommandConfig, SubCommand, ArgConfig
from .resolver import DataResolver
from .utils import VariableResolver
from .constants import CUSTOM_NAME, CUSTOM_SHORTCUT


def _save_terminal_state():
    """Save current terminal state (Unix only)."""
    if sys.platform == 'win32':
        return None
    try:
        import termios
        return termios.tcgetattr(sys.stdin)
    except Exception:
        return None


def _restore_terminal_state(old_state):
    """Restore terminal state (Unix only)."""
    if sys.platform == 'win32' or old_state is None:
        return
    try:
        import termios
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_state)
    except Exception:
        # Fallback: stty sane
        os.system('stty sane 2>/dev/null')


def _run_interactive_subprocess(cmd: str, timeout: Optional[float] = None) -> int:
    """
    Run a subprocess that may be interactive, properly handling signals.
    
    This function ensures:
    - Ctrl+C is forwarded to the subprocess (not killing the parent)
    - Ctrl+D exits the subprocess gracefully
    - Terminal state is restored after subprocess exits
    
    Args:
        cmd: The command to execute
        timeout: Optional timeout in seconds (None = no timeout)
        
    Returns:
        The subprocess return code
        
    Raises:
        subprocess.TimeoutExpired: If timeout is exceeded
    """
    terminal_state = _save_terminal_state()
    return_code = 0
    
    try:
        if sys.platform == 'win32':
            # Windows: Use CREATE_NEW_PROCESS_GROUP to isolate Ctrl+C
            # This prevents Ctrl+C from killing the parent Python process
            process = subprocess.Popen(
                cmd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise
        else:
            # Unix/macOS: Ignore SIGINT in parent, let child handle it
            # When child is in foreground, terminal sends SIGINT only to it
            original_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
            try:
                process = subprocess.Popen(cmd, shell=True)
                try:
                    return_code = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise
            finally:
                # Restore original SIGINT handler
                signal.signal(signal.SIGINT, original_sigint)
    finally:
        # Always restore terminal state
        _restore_terminal_state(terminal_state)
        # Extra safety: always reset terminal on Unix
        if sys.platform != 'win32':
            os.system('stty sane 2>/dev/null')
    
    return return_code

class CommandExecutor:
    def __init__(self, data_resolver: DataResolver):
        self.resolver = data_resolver

    def _match_alias_parts(self, alias_parts: List[str], input_parts: List[str]) -> tuple[bool, Dict[str, Any], bool]:
        # Rule 1.3.5: Allow partial match if help is requested. 
        # We don't strictly enforce length check here if we find a help flag.
        
        variables = {}
        
        # Iterate over available input parts. If input is shorter, matched will be decided by length check at end,
        # unless we find a help flag which shortcuts the process.
        for i, (alias_token, user_token) in enumerate(zip(alias_parts, input_parts)):
            # 1. Check for app variable: $${source.key} or $${source[N].key}
            app_var = VariableResolver.parse_app_var(alias_token)
            if app_var:
                # Note: index is ignored for list mode (alias matching uses all items)
                source_name, _index, key_name = app_var

                # Rule 1.3.5: Partial match help for dynamic variables too
                if user_token in ('-h', '--help'):
                    return True, variables, True

                data_list = self.resolver.resolve_one(source_name)
                if not data_list:
                    return False, {}, False
                
                found_item = None
                for item in data_list:
                    if str(item.get(key_name)) == user_token:
                        found_item = item
                        break
                
                if found_item:
                    variables[source_name] = found_item
                else:
                    return False, {}, False
                continue


            # 2. Check for user variable: ${var}
            var_name = VariableResolver.parse_user_var(alias_token)
            if var_name:
                # Rule 1.3.2: Can't use -h or --help as command args
                # But Rule 1.3.5 says partial match should show help.
                # So if we see help here, we treat it as "Partial Match Help Found" and stop.
                if user_token in ('-h', '--help'):
                    return True, variables, True
                    
                variables[var_name] = user_token
                continue

            # 3. Static match
            if alias_token != user_token:
                # Rule 1.3.5 specifically says "when variables wasnt informed".
                return False, {}, False
        
        # End of loop.
        if len(input_parts) < len(alias_parts):
            return False, {}, False
            
        return True, variables, False

    def find_command(self, args: List[str]) -> Optional[tuple[List[Union[CommandConfig, SubCommand, ArgConfig]], Dict[str, Any], bool, List[str]]]:
        for cmd in self.resolver.config.commands:
            chain, variables, is_help, remaining = self._try_match(cmd, args)
            if chain:
                return chain, variables, is_help, remaining
        return None

    def _try_match(self, command_obj: Union[CommandConfig, SubCommand], args: List[str]) -> tuple[List[Union[CommandConfig, SubCommand, ArgConfig]], Dict, bool, List[str]]:
        alias_parts = command_obj.alias.split()
        
        # 1. Match Command Alias
        matched, variables, is_help = self._match_alias_parts(alias_parts, args[:len(alias_parts)])
        
        if is_help:
            return [command_obj], variables, True, []
            
        if not matched:
            return [], {}, False, []
        
        remaining_args = args[len(alias_parts):]
        current_chain = [command_obj]

        # 2. Match Command Args (Greedy)
        while remaining_args and hasattr(command_obj, 'args') and command_obj.args:
            found_arg = False
            for arg_obj in command_obj.args:
                # Support array aliases - try each variant
                alias_variants = arg_obj.alias if isinstance(arg_obj.alias, list) else [arg_obj.alias]
                
                for alias_variant in alias_variants:
                    arg_alias_parts = alias_variant.split()
                    matched_arg, arg_vars, arg_is_help = self._match_alias_parts(arg_alias_parts, remaining_args[:len(arg_alias_parts)])
                    
                    if arg_is_help:
                        variables.update(arg_vars)
                        current_chain.append(arg_obj)
                        return current_chain, variables, True, []
                    
                    if matched_arg:
                        variables.update(arg_vars)
                        current_chain.append(arg_obj)
                        remaining_args = remaining_args[len(arg_alias_parts):]
                        found_arg = True
                        break
                
                if found_arg:
                    break
            
            if not found_arg:
                break

        # 3. Match Sub-commands
        if hasattr(command_obj, 'sub') and command_obj.sub and remaining_args:
            for sub in command_obj.sub:
                sub_chain, sub_vars, sub_is_help, sub_remaining = self._try_match(sub, remaining_args)
                if sub_chain:
                    variables.update(sub_vars)
                    return current_chain + sub_chain, variables, sub_is_help, sub_remaining
        
        # Check for help flag in remaining args
        if remaining_args and remaining_args[0] in ('-h', '--help'):
            return current_chain, variables, True, []
            
        # Success match
        return current_chain, variables, False, remaining_args

    def execute(self, command_chain: List[Union[CommandConfig, SubCommand, ArgConfig]], variables: Dict[str, Any], remaining_args: List[str] = None):
        import time
        execute_start = time.time()
        
        if remaining_args is None:
            remaining_args = []

        # Get output strategy for verbosity level
        from .output import get_output_strategy
        output = get_output_strategy(self.resolver.config.global_config.verbosity)

        # Strict mode check
        root_cmd = command_chain[0]
        # Only check strict if it's a CommandConfig (SubCommand doesn't define strict, it inherits logic or handled by root?)
        # Models say CommandConfig has strict. SubCommand does not.
        # But SubCommand is part of the chain.
        # Rule says "strict: Default false... when strict true, it will be rejected".
        # Strict applies to the COMMAND definition.
        # If I am executing a subcommand, does the strictness of the parent apply?
        # Usually strict sets the policy for the alias.
        # If I reached a subcommand, effectively I matched alias -> sub -> sub.
        # The strictness should probably check the root command config.
        
        is_strict = False
        if isinstance(root_cmd, CommandConfig):
            is_strict = root_cmd.strict
            
        if is_strict and remaining_args:
             print_formatted_text(HTML(f"<b><red>Error:</red></b> Strict mode enabled. Unknown arguments: {' '.join(remaining_args)}"))
             return

        full_template = " ".join([obj.command for obj in command_chain])
        
        # Refactored to use VariableResolver (DRY)
        
        # Determine verbose log callback
        verbose_log = output.verbose_log if output.is_verbose else None
        
        # Trace: log resolve_app_vars
        resolve_start = time.time()
        
        # 1. App Vars ($${source.key})
        cmd_resolved = VariableResolver.resolve_app_vars(
            full_template, 
            resolver_func=self.resolver.resolve_one,
            context_vars=variables,
            use_local_cache=lambda k: self.resolver.cache.get_local(k),
            verbose_log=verbose_log
        )
        
        resolve_elapsed = time.time() - resolve_start
        self.resolver.add_trace_log("VariableResolver", "resolve_app_vars", resolve_elapsed,
                                   inputs={"template": full_template[:100], "variables": variables},
                                   output_val=cmd_resolved[:100] if cmd_resolved else None)
        
        # 2. User Vars (${var})
        cmd_resolved = VariableResolver.resolve_user_vars(cmd_resolved, variables)
        
        # Append remaining args if not strict
        if remaining_args:
            # Quote arguments to preserve spaces during shell concatenation
            quoted_extras = " ".join(shlex.quote(arg) for arg in remaining_args)
            cmd_resolved += " " + quoted_extras
        
        # Flush verbose logs AFTER variable resolution (so chained resolution logs show with current command)
        self.resolver.flush_verbose_logs()
        
        # Use output strategy for Running hint and divider
        output.print_running(cmd_resolved)
        output.print_divider()
        
        try:
            timeout = 0
            if command_chain and hasattr(command_chain[0], 'timeout'):
                timeout = command_chain[0].timeout
            
            # If timeout is 0, pass None to subprocess.run (means no timeout)
            effective_timeout = timeout if timeout > 0 else None
                
            # Determine if set_locals is enabled for any command in the chain
            # Usually it applies to the leaf subcommand that is executed
            should_set_locals = any(getattr(obj, 'set_locals', False) for obj in command_chain)

            if should_set_locals:
                # Rule 4.21: Capture output, validate as simple JSON object, set locals
                # Note: set-locals commands are non-interactive, use subprocess.run
                result = subprocess.run(
                    cmd_resolved, 
                    shell=True, 
                    timeout=effective_timeout,
                    capture_output=True,
                    text=True
                )
                
                try:
                    # Validate JSON
                    if not result.stdout.strip():
                         raise ValueError("Empty output")
                         
                    output_data = json.loads(result.stdout.strip())
                    
                    if not isinstance(output_data, dict):
                         raise ValueError("Output must be a JSON object (dict), not a list or scalar")
                    
                    # Store in locals with verbose logging
                    for key, value in output_data.items():
                        self.resolver.cache.set_local(str(key), str(value))
                        output.verbose_log(f"[VERBOSE] Set local: {key} = '{value}'")
                    
                    print(json.dumps(output_data, indent=2))
                    
                    # If command failed despite valid JSON (unlikely but possible), print stderr
                    if result.returncode != 0 and result.stderr:
                         print(result.stderr)
                         
                except json.JSONDecodeError:
                    print(f"Error: Rule 4.21 - Command output must be valid JSON when set-locals is true.")
                    print(f"Output received: {result.stdout}")
                    if result.stderr:
                        print(f"Stderr: {result.stderr}")
                except ValueError as ve:
                    print(f"Error: Rule 4.21 - {ve}")
                    print(f"Output received: {result.stdout}")
                    
            else:
                # Normal execution - use interactive subprocess handler
                # This properly forwards Ctrl+C to subprocess and handles terminal state
                _run_interactive_subprocess(cmd_resolved, timeout=effective_timeout)
            
            # Reload cache from disk to pick up changes made by subprocesses (e.g., set-locals)
            # Then save to merge any parent-side changes (e.g., dynamic dict cache)
            self.resolver.cache.load()
            self.resolver.cache.save()

        except KeyboardInterrupt:
            # This should rarely happen now as SIGINT is ignored during subprocess
            print("\nOperation cancelled.")
        except subprocess.TimeoutExpired:
            print(f"\nError: Command timed out after {timeout}s")
        except Exception as e:
            print(f"Execution error: {e}")

    def print_help(self, command_chain: List[Union[CommandConfig, SubCommand, ArgConfig]]):
        """Prints helper text for the matched command chain using the appropriate formatter."""
        from .helper_formatter import get_helper_formatter
        
        print_formatted_text(HTML("\n<b><cyan>HELPER</cyan></b>\n"))
        
        # Determine helper_type from root command (CommandConfig)
        helper_type = "auto"
        if command_chain and isinstance(command_chain[0], CommandConfig):
            helper_type = command_chain[0].helper_type
        
        formatter = get_helper_formatter(helper_type)
        output = formatter.format(command_chain)
        print(output)

        print()
        print("Command Line Interface powered by Dynamic Alias")
        print(f"To display {CUSTOM_SHORTCUT} helper use --{CUSTOM_SHORTCUT}-help")
        print()

    def print_global_help(self):
        """Prints global helper text listing available dycts and commands."""
        print_formatted_text(HTML(f"\n<b><cyan>{CUSTOM_NAME} Helper</cyan></b>\n"))

        if self.resolver.config.dicts:
            print_formatted_text(HTML("<b><yellow>Dicts (Static):</yellow></b>"))
            for name in self.resolver.config.dicts:
                print(f"  - {name}")
            print()

        if self.resolver.config.dynamic_dicts:
            print_formatted_text(HTML("<b><yellow>Dynamic Dicts:</yellow></b>"))
            for name in self.resolver.config.dynamic_dicts:
                print(f"  - {name}")
            print()
        
        if self.resolver.config.commands:
            print_formatted_text(HTML("<b><yellow>Commands:</yellow></b>"))
            for cmd in self.resolver.config.commands:
                print_formatted_text(HTML(f"  <b>{cmd.name}</b> (alias: {cmd.alias})"))
                if cmd.helper:
                    for line in cmd.helper.strip().split('\n'):
                        print(f"    {line}")
                print("-" * 20)

        print()
        print("Command Line Interface powered by Dynamic Alias")
        print(f"To display {CUSTOM_SHORTCUT} helper use --{CUSTOM_SHORTCUT}-help")
        print()


