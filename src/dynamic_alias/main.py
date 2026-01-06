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

# Constants
CACHE_ENABLED = True

def _resolve_path(options: List[str], default: str) -> str:
    return next((p for p in map(os.path.expanduser, options) if os.path.exists(p)), os.path.expanduser(default))

CACHE_FILE = _resolve_path([".dya.json", "dya.json", "~/.dya.json", "~/dya.json"], "~/.dya.json")
CONFIG_FILE = _resolve_path([".dya.yaml", "dya.yaml", "~/.dya.yaml", "~/dya.yaml"], "~/.dya.yaml")

def main():
    loader = ConfigLoader(CONFIG_FILE)
    loader.load()
    
    cache = CacheManager(CACHE_FILE, CACHE_ENABLED)
    cache.load()
    
    resolver = DataResolver(loader, cache)
    resolver.resolve_all()
    
    executor = CommandExecutor(resolver)

    if len(sys.argv) > 1:
        args = sys.argv[1:]
        result = executor.find_command(args)
        if result:
            cmd, vars = result
            executor.execute(cmd, vars)
            cache.save()
        else:
            print("Error: Command not found.")
    else:
        shell = InteractiveShell(resolver, executor)
        shell.run()

if __name__ == "__main__":
    main()
