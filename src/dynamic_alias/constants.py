import os
import sys

# Defaults
DEFAULT_SHORTCUT = "dya"
DEFAULT_NAME = "DYNAMIC ALIAS"

def get_config_from_toml():
    """Try to read from pyproject.toml"""
    try:
        # Assuming src/dynamic_alias/constants.py, go up 3 levels
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        toml_path = os.path.join(base_dir, "pyproject.toml")
        
        if not os.path.exists(toml_path):
            # Fallback: check current directory (common in dev/test)
            cwd_toml = os.path.abspath("pyproject.toml")
            if os.path.exists(cwd_toml):
                toml_path = cwd_toml
        
        if os.path.exists(toml_path):
            with open(toml_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            import re
            
            shortcut = DEFAULT_SHORTCUT
            name = DEFAULT_NAME
            
            custom_section = re.search(r'^\[custom-build\]', content, re.MULTILINE)
            if custom_section:
                start = custom_section.end()
                next_section = re.search(r'^\[', content[start:], re.MULTILINE)
                end = start + next_section.start() if next_section else len(content)
                section_text = content[start:end]
                
                for line in section_text.splitlines():
                    line = line.strip()
                    if line.startswith('shortcut'):
                        parts = line.split('=')
                        if len(parts) == 2:
                            val = parts[1].strip().strip('"\'')
                            shortcut = val
                    elif line.startswith('name'):
                        parts = line.split('=')
                        if len(parts) == 2:
                            val = parts[1].strip().strip('"\'')
                            name = val
                            
            return shortcut, name
            
    except Exception:
        pass
    return DEFAULT_SHORTCUT, DEFAULT_NAME

CUSTOM_SHORTCUT, CUSTOM_NAME = get_config_from_toml()

# Regex Patterns
# Matches $${source.key} OR $${source[N].key} for indexed access
# Groups: (1) source, (2) index or None, (3) key
REGEX_APP_VAR = r'\$\$\{(\w+)(?:\[(\d+)\])?\.(\w+)\}'
REGEX_USER_VAR = r'\$\{(\w+)\}'          # Matches ${var}

# Configuration CONSTANTS (Moved from validator.py)
REQUIRED_FIELDS = {
    'dict': ['type', 'name', 'data'],
    'dynamic_dict': ['type', 'name', 'command', 'mapping'],
    'command': ['type', 'name', 'alias', 'command'],
}

OPTIONAL_FIELDS = {
    'dict': [],
    'dynamic_dict': ['priority', 'timeout', 'cache-ttl'],
    'command': ['helper', 'helper_type', 'sub', 'args', 'timeout', 'strict', 'set-locals'],
}

CONFIG_KEYS = [
    'style-completion', 'style-completion-current', 
    'style-scrollbar-background', 'style-scrollbar-button',
    'style-placeholder-color', 'style-placeholder-text',
    'history-size', 'verbosity', 'shell'
]

# Cache Key Constants (DRY: single source of truth for cache keys)
CACHE_KEY_HISTORY = '_history'
CACHE_KEY_LOCALS = '_locals'
CACHE_KEY_TIMESTAMP = 'timestamp'
CACHE_KEY_DATA = 'data'
CACHE_KEY_CRYPT = '_crypt'  # Rule 1.2.28: Encrypted cache data key

# Verbosity Levels
VERBOSITY_SILENT = "silent"
VERBOSITY_DEFAULT = "default"
VERBOSITY_VERBOSE = "verbose"
VERBOSITY_TRACE = "trace"
VERBOSITY_LEVELS = [VERBOSITY_SILENT, VERBOSITY_DEFAULT, VERBOSITY_VERBOSE, VERBOSITY_TRACE]
