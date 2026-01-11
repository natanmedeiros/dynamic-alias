import sys
import os
from typing import List

# Add parent directory to path to allow running as script if needed, 
# though checking __package__ is better for installed packages.
# For local dev without install:
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from .config import ConfigLoader
from .cache import CacheManager
from .resolver import DataResolver
from .executor import CommandExecutor
from .shell import InteractiveShell
from .constants import CUSTOM_SHORTCUT

# Constants
CACHE_ENABLED = True

def _resolve_path(options: List[str], default: str) -> str:
    return next((p for p in map(os.path.expanduser, options) if os.path.exists(p)), os.path.expanduser(default))

def main():
    # 1. Parse app-level flags
    args = sys.argv[1:]
    
    config_flag = f"--{CUSTOM_SHORTCUT}-config"
    cache_flag = f"--{CUSTOM_SHORTCUT}-cache"
    
    config_file_override = None
    cache_file_override = None
    
    filtered_args = []
    
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == config_flag:
            if i + 1 < len(args):
                config_file_override = args[i+1]
                i += 2
                continue
            else:
                print(f"Error: {config_flag} requires an argument")
                sys.exit(1)
        elif arg == cache_flag:
            if i + 1 < len(args):
                cache_file_override = args[i+1]
                i += 2
                continue
            else:
                print(f"Error: {cache_flag} requires an argument")
                sys.exit(1)
        else:
            filtered_args.append(arg)
            i += 1
            
    # 2. Resolve Paths
    if config_file_override:
        final_config_path = os.path.expanduser(config_file_override)
    else:
        path_options_yaml = [f".{CUSTOM_SHORTCUT}.yaml", f"{CUSTOM_SHORTCUT}.yaml", f"~/.{CUSTOM_SHORTCUT}.yaml", f"~/{CUSTOM_SHORTCUT}.yaml"]
        default_yaml = f"~/.{CUSTOM_SHORTCUT}.yaml"
        final_config_path = _resolve_path(path_options_yaml, default_yaml)

    if cache_file_override:
        final_cache_path = os.path.expanduser(cache_file_override)
    else:
        path_options_json = [f".{CUSTOM_SHORTCUT}.json", f"{CUSTOM_SHORTCUT}.json", f"~/.{CUSTOM_SHORTCUT}.json", f"~/{CUSTOM_SHORTCUT}.json"]
        default_json = f"~/.{CUSTOM_SHORTCUT}.json"
        final_cache_path = _resolve_path(path_options_json, default_json)

    # 3. Load App
    loader = ConfigLoader(final_config_path)
    loader.load()
    
    cache = CacheManager(final_cache_path, CACHE_ENABLED)
    cache.load()
    
    resolver = DataResolver(loader, cache)
    # Don't resolve_all() at startup - use lazy loading
    # resolve_all() is only called for non-interactive command execution
    
    executor = CommandExecutor(resolver)

    if filtered_args:
        # Global help check
        if len(filtered_args) == 1 and filtered_args[0] in ('-h', '--help'):
            executor.print_global_help()
            return

        # Non-interactive mode also uses lazy loading
        # resolve_one() is called during find_command and execute as needed
        
        result = executor.find_command(filtered_args)
        if result:
            cmd, vars, is_help, remaining = result
            if is_help:
                executor.print_help(cmd)
            else:
                executor.execute(cmd, vars, remaining)
            # Save cache after execution (captures any resolved dicts)
            cache.save()
        else:
            print("Error: Command not found.")
    else:
        # Interactive mode - lazy loading via resolve_one() in completer
        shell = InteractiveShell(resolver, executor)
        shell.run()

if __name__ == "__main__":
    main()
