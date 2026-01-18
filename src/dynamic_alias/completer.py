import re
import os
import shlex
from prompt_toolkit.completion import Completer, Completion
from .resolver import DataResolver
from .executor import CommandExecutor
from .constants import REGEX_APP_VAR, WINDOWS_BUILTINS, UNIX_BUILTINS

# Cache for system commands (populated lazily)
_system_commands_cache = None

def get_system_commands():
    """Get list of executable commands from PATH (cached)."""
    global _system_commands_cache
    if _system_commands_cache is not None:
        return _system_commands_cache
    
    commands = set()
    
    # Add common shell built-ins
    if os.name == 'nt':
        # Common Windows built-ins
        commands.update(WINDOWS_BUILTINS)
    else:
        # Common Unix built-ins
        commands.update(UNIX_BUILTINS)


    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    
    for path_dir in path_dirs:
        if not os.path.isdir(path_dir):
            continue
        try:
            for item in os.listdir(path_dir):
                full_path = os.path.join(path_dir, item)
                # On Windows, check for .exe, .cmd, .bat, etc.
                if os.name == 'nt':
                    name_lower = item.lower()
                    if any(name_lower.endswith(ext) for ext in ('.exe', '.cmd', '.bat', '.ps1', '.com')):
                        # Add without extension for cleaner completion
                        base_name = os.path.splitext(item)[0]
                        commands.add(base_name.lower())
                else:
                    # On Unix, check if executable
                    if os.access(full_path, os.X_OK) and os.path.isfile(full_path):
                        commands.add(item)
        except (PermissionError, OSError):
            continue
    
    _system_commands_cache = sorted(commands)
    return _system_commands_cache

class DynamicAliasCompleter(Completer):
    def __init__(self, resolver: DataResolver, executor: CommandExecutor):
        self.resolver = resolver
        self.executor = executor

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        try:
            parts = shlex.split(text)
        except ValueError:
            # Invalid quotes or other shlex parsing errors
            return

        if not parts:
            parts = ['']
        
        elif text.endswith(' '):
            parts.append('')
        
        # Parse context
        # We need to traverse the command tree consistent with the input
        
        scope = self.resolver.config.commands
        used_args_in_scope = set() # Aliases of used args
        
        # Cursor tracking
        part_idx = 0
        
        matched_cmd_node = None # The last command/subcommand matched
        pending_arg = None # If we are in the middle of an arg (alias match start but not full)
        
        # We process all parts EXCEPT the last one (which is the one being completed)
        # However, to track context, we try to match as much as possible.
        
        while part_idx < len(parts) - 1:
            token = parts[part_idx]
            match_found = False
            
            # 1. Try Commands/Subs in scope
            start_parts_slice = parts[part_idx:] 
            
            for cmd in scope:
                cmd_parts = cmd.alias.split()
                if part_idx + len(cmd_parts) <= len(parts) - 1:
                     is_match, _, _ = self.executor._match_alias_parts(cmd_parts, parts[part_idx:part_idx+len(cmd_parts)])
                     if is_match:
                         matched_cmd_node = cmd
                         part_idx += len(cmd_parts)
                         scope = cmd.sub if hasattr(cmd, 'sub') else []
                         used_args_in_scope = set() 
                         match_found = True
                         break
            
            if match_found:
                continue
                
            # 2. Try match ARGS in (matched_cmd_node) context
            if matched_cmd_node and hasattr(matched_cmd_node, 'args'):
                for arg in matched_cmd_node.args:
                    # Get all alias variants (could be string or list)
                    alias_variants = arg.alias if isinstance(arg.alias, list) else [arg.alias]
                    primary_alias = alias_variants[0]
                    
                    if primary_alias in used_args_in_scope:
                        continue
                    
                    # Try matching any variant
                    for alias_variant in alias_variants:
                        arg_parts = alias_variant.split()
                        if part_idx + len(arg_parts) <= len(parts) - 1:
                            is_match, _, _ = self.executor._match_alias_parts(arg_parts, parts[part_idx:part_idx+len(arg_parts)])
                            if is_match:
                                used_args_in_scope.add(primary_alias)
                                part_idx += len(arg_parts)
                                match_found = True
                                break
                    if match_found:
                        break
            
            if match_found:
                continue

            break
            
        # End of consumption loop.
        # matched_cmd_node is the active command.
        # part_idx points to where we are completions.
        
        # Check if we are incomplete on a multi-token structure (Command or Arg)
        
        prefix = parts[-1]
        
        # If part_idx is NOT at len(parts)-1, it means we stopped consuming before the end.
        # This implies we are "inside" a multi-token structure or invalid input.
        
        if part_idx < len(parts) - 1:
            # We have some tokens that didn't fully match a structure.
            # e.g. `pg db1 -o` (and we are at `''`?)
            # No, if `pg db1 -o `, parts=`['-o', '']`. part_idx matches `-o`.
            # Wait, my loop condition `part_idx < len(parts) - 1`.
            # If `parts` = `['...','-o', '']`.
            # part_idx is at `-o`.
            # If `-o` is start of arg `-o ${file}`.
            
            # Check for Partial Matches starting at part_idx
            
            # 1. Partial Arg?
            if matched_cmd_node and hasattr(matched_cmd_node, 'args'):
                for arg in matched_cmd_node.args:
                    alias_variants = arg.alias if isinstance(arg.alias, list) else [arg.alias]
                    primary_alias = alias_variants[0]
                    
                    if primary_alias in used_args_in_scope:
                        continue
                    
                    for alias_variant in alias_variants:
                        arg_parts = alias_variant.split()
                    # Check prefix match
                    # We have `parts[part_idx : -1]` (Completed tokens after match)
                    # And `parts[-1]` (Typing)
                    
                    # Consumed so far: `parts[part_idx:len(parts)-1]`
                    consumed_chunk = parts[part_idx:len(parts)-1]
                    
                    # Does this chunk match the start of arg_parts?
                    if len(consumed_chunk) < len(arg_parts):
                        # Potential match
                        is_match, _, _ = self.executor._match_alias_parts(arg_parts[:len(consumed_chunk)], consumed_chunk)
                        if is_match:
                            # We are inside this arg.
                            # What is the expected next token?
                            next_token_idx = len(consumed_chunk)
                            expected_token_alias = arg_parts[next_token_idx]
                            
                            # Suggestions
                            # If expected token is variable `${...}`, Do NOT yield (Rule 4.18)
                            # If expected token is static, yield it if matches prefix
                            if expected_token_alias.startswith('$${'):
                                yield Completion(expected_token_alias + ' ', start_position=-len(prefix), display=expected_token_alias)
                            elif expected_token_alias.startswith('${'):
                                # User rule: Args can autocomplete only flags, not user variables
                                pass 
                            else:
                                if expected_token_alias.startswith(prefix):
                                    yield Completion(expected_token_alias + ' ', start_position=-len(prefix))
                            
                            # If we matched a partial arg, we return (exclusive?)
                            return

            # 2. Partial Command?
            for cmd in scope:
                cmd_parts = cmd.alias.split()
                # Check prefix match
                # Consumed so far: parts[part_idx:len(parts)-1]
                consumed_chunk = parts[part_idx:len(parts)-1]
                
                if not consumed_chunk:
                    continue
                    
                if len(consumed_chunk) < len(cmd_parts):
                    # Check if consumed chunk matches start of alias
                    is_match, _, _ = self.executor._match_alias_parts(cmd_parts[:len(consumed_chunk)], consumed_chunk)
                    if is_match:
                        # We are inside this command alias
                        next_token_idx = len(consumed_chunk)
                        expected_token_alias = cmd_parts[next_token_idx]
                        
                        # Suggestion logic
                        # Dynamic Var $${...}
                        app_var_match = re.match(REGEX_APP_VAR, expected_token_alias)
                        if app_var_match:
                            # Groups: (1) source, (2) optional index, (3) key
                            source, key = app_var_match.group(1), app_var_match.group(3)
                            # Lazy load: only resolve this dict when needed
                            data = self.resolver.resolve_one(source)
                            for item in data:
                                val = str(item.get(key, ''))
                                if val.startswith(prefix):
                                    yield Completion(val + ' ', start_position=-len(prefix))
                        
                        # User Var ${...}
                        elif expected_token_alias.startswith('${'):
                             # Rule 4.20: Avoid user defined variables completion like ${sql_text}
                             pass
                             # yield Completion(expected_token_alias, start_position=-len(prefix), display=expected_token_alias)
                             
                        # Static Text
                        else:
                            if expected_token_alias.startswith(prefix):
                                yield Completion(expected_token_alias + ' ', start_position=-len(prefix))
                        
                        # If we found a partial command match, we should probably stop?
                        # Or continue to find distinct aliases? 
                        # Return to yield exclusive results for this alias path?
                        # Yes, finding specific command path.
                        # But wait, multiple commands might share prefix?
                        # e.g. `s3 sync` and `s3 ls`.
                        # If we typed `s3 `, we match both!
                        # We should yield from ALL matches, not return immediately.
                        # So don't return.
                        pass
        else:
            # part_idx == len(parts) - 1.
            
            # Suggestions:
            # 1. Subcommands of matched_cmd_node
            # 2. Unused Args of matched_cmd_node
            
            candidates = []
            
            if matched_cmd_node:
                # Subs
                if hasattr(matched_cmd_node, 'sub'):
                    candidates.extend(matched_cmd_node.sub)
                
                # Args (unused)
                if hasattr(matched_cmd_node, 'args'):
                    for arg in matched_cmd_node.args:
                        alias_variants = arg.alias if isinstance(arg.alias, list) else [arg.alias]
                        primary_alias = alias_variants[0]
                        if primary_alias not in used_args_in_scope:
                            candidates.append(arg)
            else:
                # Root commands
                candidates.extend(self.resolver.config.commands)
            
            for cand in candidates:
                # First token of alias (use primary alias for candidates)
                cand_alias = cand.alias[0] if isinstance(cand.alias, list) else cand.alias
                cand_parts = cand_alias.split()
                head = cand_parts[0]
                
                # Handling dynamic vars $${...}
                app_var_match = re.match(REGEX_APP_VAR, head)
                if app_var_match:
                    # Groups: (1) source, (2) optional index, (3) key
                    source, key = app_var_match.group(1), app_var_match.group(3)
                    # Lazy load: only resolve this dict when needed
                    data = self.resolver.resolve_one(source)
                    for item in data:
                        val = str(item.get(key, ''))
                        if val.startswith(prefix):
                            yield Completion(val + ' ', start_position=-len(prefix))
                elif head.startswith('${'):
                     # User var placeholder as start of command? Rare but possible.
                     yield Completion(head + ' ', start_position=-len(prefix))
                else:
                    if head.startswith(prefix):
                        yield Completion(head + ' ', start_position=-len(prefix))
            
            # Path completion: complete system commands from PATH
            # Only when: shell: true AND path_completion: true AND no command matched AND at first token
            global_config = self.resolver.config.global_config
            if (global_config.shell and 
                global_config.path_completion and 
                matched_cmd_node is None and 
                len(parts) == 1 and 
                prefix):
                
                # Get matching system commands (inline completion, not dropdown)
                system_cmds = get_system_commands()
                for cmd in system_cmds:
                    if cmd.startswith(prefix.lower()) and cmd != prefix.lower():
                        # Yield only the best match (first alphabetically)
                        yield Completion(cmd + ' ', start_position=-len(prefix), display=cmd)
                        break  # Only complete to first match (inline, not list)

