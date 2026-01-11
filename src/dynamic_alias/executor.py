import re
import subprocess
import shlex
from typing import Dict, List, Any, Optional, Union
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from .models import CommandConfig, SubCommand, ArgConfig
from .resolver import DataResolver
from .constants import CUSTOM_NAME

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
            # 1. Check for app variable: $${source.key}
            app_var_match = re.match(r'\$\$\{(\w+)\.(\w+)\}', alias_token)
            if app_var_match:
                # Rule 1.3.5: Partial match help for dynamic variables too
                if user_token in ('-h', '--help'):
                    return True, variables, True

                source_name = app_var_match.group(1) 
                key_name = app_var_match.group(2)    
                
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
            user_var_match = re.match(r'\$\{(\w+)\}', alias_token)
            if user_var_match:
                # Rule 1.3.2: Can't use -h or --help as command args
                # But Rule 1.3.5 says partial match should show help.
                # So if we see help here, we treat it as "Partial Match Help Found" and stop.
                if user_token in ('-h', '--help'):
                    return True, variables, True
                    
                var_name = user_var_match.group(1)
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
                arg_alias_parts = arg_obj.alias.split()
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
        
        if remaining_args is None:
            remaining_args = []

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
        
        def app_var_replace(match):
            source = match.group(1)
            key = match.group(2)
            if source in variables and isinstance(variables[source], dict):
                return str(variables[source].get(key, match.group(0)))
            return match.group(0)

        cmd_resolved = re.sub(r'\$\$\{(\w+)\.(\w+)\}', app_var_replace, full_template)
        
        def user_var_replace(match):
            key = match.group(1)
            if key in variables and isinstance(variables[key], str):
                return variables[key]
            return match.group(0)

        cmd_resolved = re.sub(r'\$\{(\w+)\}', user_var_replace, cmd_resolved)
        
        # Append remaining args if not strict
        if remaining_args:
            # Quote arguments to preserve spaces during shell concatenation
            quoted_extras = " ".join(shlex.quote(arg) for arg in remaining_args)
            cmd_resolved += " " + quoted_extras
        
        print_formatted_text(HTML(f"<b><green>Running:</green></b> {cmd_resolved}"))
        print("-" * 30)
        
        try:
            timeout = 0
            if command_chain and hasattr(command_chain[0], 'timeout'):
                timeout = command_chain[0].timeout
            
            # If timeout is 0, pass None to subprocess.run (means no timeout)
            effective_timeout = timeout if timeout > 0 else None
                
            subprocess.run(cmd_resolved, shell=True, timeout=effective_timeout)
            
            # Save valid cache state (dynamic dicts)
            self.resolver.cache.save()

        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except subprocess.TimeoutExpired:
            print(f"\nError: Command timed out after {timeout}s")
        except Exception as e:
            print(f"Execution error: {e}")

    def print_help(self, command_chain: List[Union[CommandConfig, SubCommand, ArgConfig]]):
        """Prints helper text for the matched command chain."""
        print_formatted_text(HTML("\n<b><cyan>HELPER</cyan></b>\n"))
        
        found_help = False
        for obj in command_chain:
            if obj.helper:
                found_help = True
                print_formatted_text(HTML(f"<b><yellow>Command:</yellow></b> {obj.alias}"))
                print(obj.helper.strip())
                print("-" * 20)
        
        if not found_help:
            print("No helper information available for this command.")

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


