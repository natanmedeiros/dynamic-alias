import re
import os
from typing import List, Dict, Any, Callable, Optional, Tuple, Set
from .constants import REGEX_APP_VAR, REGEX_USER_VAR

class VariableResolver:
    """Helper class for variable substitution (DRY compliance)."""
    
    @staticmethod
    def extract_app_vars(text: str) -> Set[Tuple[str, Optional[str], str]]:
        """
        Extract all $${source.key} or $${source[N].key} references.
        Returns: Set of (source, index_or_None, key) tuples
        """
        if not isinstance(text, str):
            return set()
        return set(re.findall(REGEX_APP_VAR, text))

    @staticmethod
    def resolve_app_vars(text: str, resolver_func: Callable[[str], List[Dict]], 
                         context_vars: Dict[str, Any] = None, use_local_cache: Callable[[str], Any] = None,
                         verbose_log: Callable[[str], None] = None) -> str:
        """
        Replace $${source.key} or $${source[N].key} in text using specific resolver logic.
        
        Args:
            text: The text string to process
            resolver_func: Callback(source_name) -> List[Dict] (returns data list or empty list)
            context_vars: Optional dict of variables already resolved context (e.g. from alias match)
            use_local_cache: Optional callback(key) -> value for resolving $${locals.key}
            verbose_log: Optional callback(message) for verbose logging
        
        Access Modes:
            - List Mode (context_vars): Uses matched item, ignores index
            - Direct Mode: Uses specified index or defaults to 0
        """
        if context_vars is None:
            context_vars = {}

        def replace(match):
            source = match.group(1)
            index_str = match.group(2)  # None or "N" string
            key = match.group(3)
            
            # Parse index: default to 0 if not specified
            index = int(index_str) if index_str else 0
            
            # 1. Handle locals (priority 1) - Rule 1.2.25
            if source == 'locals' and use_local_cache:
                val = use_local_cache(key)
                if val is not None:
                    if verbose_log:
                        verbose_log(f"[VERBOSE] Resolved $${{locals.{key}}} = '{val}'")
                    return str(val)
                return match.group(0)

            # 2. Handle context vars (priority 2) - List Mode
            # If source is in context AND no explicit index, use the matched item
            # Explicit index [N] forces direct mode even if source is in context
            if source in context_vars and index_str is None:
                item = context_vars[source]
                if isinstance(item, dict):
                    resolved_val = str(item.get(key, match.group(0)))
                    if verbose_log:
                        verbose_log(f"[VERBOSE] Resolved $${{{source}.{key}}} = '{resolved_val}' (from context)")
                    return resolved_val
            
            # 3. Handle lazy resolution (priority 3) - Direct Mode
            # Resolve source on demand and use specified index (default 0)
            data_list = resolver_func(source)
            if data_list:
                # Validate index bounds
                if index < len(data_list):
                    resolved_val = str(data_list[index].get(key, match.group(0)))
                    if verbose_log:
                        index_display = f"[{index}]" if index_str else ""
                        verbose_log(f"[VERBOSE] Resolved $${{{source}{index_display}.{key}}} = '{resolved_val}'")
                    return resolved_val
                else:
                    # Index out of bounds - log warning and return original
                    print(f"Warning: Index {index} out of bounds for '{source}' (size: {len(data_list)})")
                    return match.group(0)
                
            return match.group(0)
            
        return re.sub(REGEX_APP_VAR, replace, text)

    @staticmethod
    def resolve_user_vars(text: str, variables: Dict[str, str]) -> str:
        """Replace ${var} with values from variables dict."""
        def replace(match):
            key = match.group(1)
            if key in variables and isinstance(variables[key], str):
                return variables[key]
            return match.group(0)
        
        return re.sub(REGEX_USER_VAR, replace, text)

    @staticmethod
    def parse_app_var(text: str) -> Optional[Tuple[str, Optional[str], str]]:
        """
        Check if text is $${source.key} or $${source[N].key}.
        Returns: (source, index_or_None, key) or None
        """
        match = re.fullmatch(REGEX_APP_VAR, text)
        if match:
            return match.group(1), match.group(2), match.group(3)
        return None

    @staticmethod
    def parse_user_var(text: str) -> Optional[str]:
        """Check if text is ${var} and return var_name."""
        match = re.fullmatch(REGEX_USER_VAR, text)
        if match:
            return match.group(1)
        return None


def resolve_path(options: List[str], default: str) -> str:
    """Resolve path from options, checking existence, fallback to default."""
    return next((p for p in map(os.path.expanduser, options) 
                if os.path.exists(p)), os.path.expanduser(default))
