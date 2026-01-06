import re
import subprocess
from typing import Dict, List, Any, Optional, Union
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from .models import CommandConfig, SubCommand, ArgConfig, DEFAULT_TIMEOUT
from .resolver import DataResolver

class CommandExecutor:
    def __init__(self, data_resolver: DataResolver):
        self.resolver = data_resolver

    def _match_alias_parts(self, alias_parts: List[str], input_parts: List[str]) -> tuple[bool, Dict[str, Any]]:
        if len(input_parts) < len(alias_parts):
            return False, {}

        variables = {}
        for alias_token, user_token in zip(alias_parts, input_parts):
            # 1. Check for app variable: $${source.key}
            app_var_match = re.match(r'\$\$\{(\w+)\.(\w+)\}', alias_token)
            if app_var_match:
                source_name = app_var_match.group(1) 
                key_name = app_var_match.group(2)    
                
                data_list = self.resolver.resolved_data.get(source_name)
                if not data_list:
                    return False, {}
                
                found_item = None
                for item in data_list:
                    if str(item.get(key_name)) == user_token:
                        found_item = item
                        break
                
                if found_item:
                    variables[source_name] = found_item
                else:
                    return False, {} 
                continue

            # 2. Check for user variable: ${var}
            user_var_match = re.match(r'\$\{(\w+)\}', alias_token)
            if user_var_match:
                var_name = user_var_match.group(1)
                variables[var_name] = user_token
                continue

            # 3. Static match
            if alias_token != user_token:
                return False, {}
        
        return True, variables

    def find_command(self, args: List[str]) -> Optional[tuple[List[Union[CommandConfig, SubCommand, ArgConfig]], Dict[str, Any]]]:
        for cmd in self.resolver.config.commands:
            chain, variables = self._try_match(cmd, args)
            if chain:
                return chain, variables
        return None

    def _try_match(self, command_obj: Union[CommandConfig, SubCommand], args: List[str]) -> tuple[List[Union[CommandConfig, SubCommand, ArgConfig]], Dict]:
        alias_parts = command_obj.alias.split()
        
        # 1. Match Command Alias
        matched, variables = self._match_alias_parts(alias_parts, args[:len(alias_parts)])
        if not matched:
            return [], {}
        
        remaining_args = args[len(alias_parts):]
        current_chain = [command_obj]

        # 2. Match Command Args (Greedy)
        while remaining_args and hasattr(command_obj, 'args') and command_obj.args:
            found_arg = False
            for arg_obj in command_obj.args:
                arg_alias_parts = arg_obj.alias.split()
                matched_arg, arg_vars = self._match_alias_parts(arg_alias_parts, remaining_args[:len(arg_alias_parts)])
                
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
                sub_chain, sub_vars = self._try_match(sub, remaining_args)
                if sub_chain:
                    variables.update(sub_vars)
                    return current_chain + sub_chain, variables
        
        if not remaining_args:
             return current_chain, variables
             
        return [], {}

    def execute(self, command_chain: List[Union[CommandConfig, SubCommand, ArgConfig]], variables: Dict[str, Any]):
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
        
        print_formatted_text(HTML(f"<b><green>Running:</green></b> {cmd_resolved}"))
        print("-" * 30)
        
        try:
            timeout = DEFAULT_TIMEOUT
            if command_chain and hasattr(command_chain[0], 'timeout'):
                timeout = command_chain[0].timeout
                
            subprocess.run(cmd_resolved, shell=True, timeout=timeout)

        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except subprocess.TimeoutExpired:
            print(f"\nError: Command timed out after {timeout}s")
        except Exception as e:
            print(f"Execution error: {e}")
