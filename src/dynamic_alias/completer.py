import re
import shlex
from prompt_toolkit.completion import Completer, Completion
from .resolver import DataResolver
from .executor import CommandExecutor

class DynamicAliasCompleter(Completer):
    def __init__(self, resolver: DataResolver, executor: CommandExecutor):
        self.resolver = resolver
        self.executor = executor

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        try:
            parts = shlex.split(text)
        except:
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
                    if arg.alias in used_args_in_scope:
                        continue
                    
                    arg_parts = arg.alias.split()
                    if part_idx + len(arg_parts) <= len(parts) - 1:
                        is_match, _, _ = self.executor._match_alias_parts(arg_parts, parts[part_idx:part_idx+len(arg_parts)])
                        if is_match:
                             used_args_in_scope.add(arg.alias)
                             part_idx += len(arg_parts)
                             match_found = True
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
                    if arg.alias in used_args_in_scope:
                        continue
                    arg_parts = arg.alias.split()
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
                                yield Completion(expected_token_alias, start_position=-len(prefix), display=expected_token_alias)
                            elif expected_token_alias.startswith('${'):
                                # User rule: Args can autocomplete only flags, not user variables
                                pass 
                            else:
                                if expected_token_alias.startswith(prefix):
                                    yield Completion(expected_token_alias, start_position=-len(prefix))
                            
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
                        app_var_match = re.match(r'\$\$\{(\w+)\.(\w+)\}', expected_token_alias)
                        if app_var_match:
                            source, key = app_var_match.group(1), app_var_match.group(2)
                            # Lazy load: only resolve this dict when needed
                            data = self.resolver.resolve_one(source)
                            for item in data:
                                val = str(item.get(key, ''))
                                if val.startswith(prefix):
                                    yield Completion(val, start_position=-len(prefix))
                        
                        # User Var ${...}
                        elif expected_token_alias.startswith('${'):
                             # Rule 4.20: Avoid user defined variables completion like ${sql_text}
                             pass
                             # yield Completion(expected_token_alias, start_position=-len(prefix), display=expected_token_alias)
                             
                        # Static Text
                        else:
                            if expected_token_alias.startswith(prefix):
                                yield Completion(expected_token_alias, start_position=-len(prefix))
                        
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
                        if arg.alias not in used_args_in_scope:
                            candidates.append(arg)
            else:
                # Root commands
                candidates.extend(self.resolver.config.commands)
            
            for cand in candidates:
                # First token of alias
                cand_parts = cand.alias.split()
                head = cand_parts[0]
                
                # Handling dynamic vars $${...}
                app_var_match = re.match(r'\$\$\{(\w+)\.(\w+)\}', head)
                if app_var_match:
                    source, key = app_var_match.group(1), app_var_match.group(2)
                    # Lazy load: only resolve this dict when needed
                    data = self.resolver.resolve_one(source)
                    for item in data:
                        val = str(item.get(key, ''))
                        if val.startswith(prefix):
                            yield Completion(val, start_position=-len(prefix))
                elif head.startswith('${'):
                     # User var placeholder as start of command? Rare but possible.
                     yield Completion(head, start_position=-len(prefix))
                else:
                    if head.startswith(prefix):
                        yield Completion(head, start_position=-len(prefix))
