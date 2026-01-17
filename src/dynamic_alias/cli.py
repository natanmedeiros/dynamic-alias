import sys
import os
import shutil
import hashlib
from typing import List, Optional

from .config import ConfigLoader
from .cache import CacheManager
from .resolver import DataResolver
from .executor import CommandExecutor
from .shell import InteractiveShell
from .validator import ConfigValidator, print_validation_report, validate_config_silent
from .constants import CUSTOM_SHORTCUT, CUSTOM_NAME
from .utils import resolve_path

class DynamicAliasCLI:
    """Encapsulates the CLI logic for Dynamic Alias."""
    
    def __init__(self):
        self.config_flag = f"--{CUSTOM_SHORTCUT}-config"
        self.cache_flag = f"--{CUSTOM_SHORTCUT}-cache"
        self.validate_flag = f"--{CUSTOM_SHORTCUT}-validate"
        self.clear_cache_flag = f"--{CUSTOM_SHORTCUT}-clear-cache"
        self.clear_history_flag = f"--{CUSTOM_SHORTCUT}-clear-history"
        self.clear_all_flag = f"--{CUSTOM_SHORTCUT}-clear-all"
        self.set_locals_flag = f"--{CUSTOM_SHORTCUT}-set-locals"
        self.clear_locals_flag = f"--{CUSTOM_SHORTCUT}-clear-locals"
        self.dump_flag = f"--{CUSTOM_SHORTCUT}-dump"
        self.dya_help_flag = f"--{CUSTOM_SHORTCUT}-help"

    def run(self):
        """Main entry point."""
        args = sys.argv[1:]
        
        # Parse Flags
        parsed = self._parse_args(args)
        if parsed.should_exit:
            return

        # Handle Application Help
        if self.dya_help_flag in parsed.filtered_args:
            self._print_app_help()
            return
            
        # 2. Resolve Paths
        final_config_path, final_cache_path = self._resolve_paths(parsed)

        # Handle validation
        if parsed.run_validation:
            validator = ConfigValidator(final_config_path)
            report = validator.validate()
            exit_code = print_validation_report(report, CUSTOM_SHORTCUT)
            sys.exit(exit_code)
            
        # Handle Cache/Locals Management
        if self._handle_management_flags(parsed, final_cache_path, final_config_path):
            return

        # Ensure Config (SHA Check)
        self._ensure_default_config()

        # Load App
        self._execute_app(parsed.filtered_args, final_config_path, final_cache_path)

    def _execute_app(self, filtered_args: List[str], config_path: str, cache_path: str):
        import time
        
        # Load config with timing
        config_start = time.time()
        loader = ConfigLoader(config_path)
        try:
            loader.load()
        except FileNotFoundError as e:
            # Rule 1.3.8: Handle missing config
            is_help_request = (len(filtered_args) == 1 and filtered_args[0] in ('-h', '--help'))
            if is_help_request:
                print(f"Error: {e}")
                print("\n" + "="*30 + "\n")
                self._print_app_help()
                return
            else:
                print(f"Error: {e}")
                sys.exit(1)
        config_elapsed = time.time() - config_start
        
        # Get output strategy for verbosity level
        from .output import get_output_strategy
        output = get_output_strategy(loader.global_config.verbosity)
        output.verbose_log(f"[VERBOSE] Loaded configuration from: {config_path}")
        output.trace_log("ConfigLoader", "load", config_elapsed,
                        inputs={"path": config_path},
                        output=f"{len(loader.commands)} commands, {len(loader.dicts)} dicts, {len(loader.dynamic_dicts)} dynamic_dicts")
        
        # Silent validation at startup with timing
        validation_start = time.time()
        if not validate_config_silent(config_path, CUSTOM_SHORTCUT):
            sys.exit(1)
        validation_elapsed = time.time() - validation_start
        output.trace_log("ConfigValidator", "validate", validation_elapsed,
                        inputs={"path": config_path},
                        output="passed")
        
        # Load cache with timing
        cache_start = time.time()
        cache = CacheManager(cache_path, True) # CACHE_ENABLED is typically True
        cache_existed = os.path.exists(cache_path)
        cache.load()
        cache_elapsed = time.time() - cache_start
        
        if cache_existed:
            output.verbose_log(f"[VERBOSE] Loaded cache from: {cache_path}")
        else:
            output.verbose_log(f"[VERBOSE] Created new cache file: {cache_path}")
        
        history = cache.get_history()
        if history:
            output.verbose_log(f"[VERBOSE] Loaded {len(history)} history entries")
        
        output.trace_log("CacheManager", "load", cache_elapsed,
                        inputs={"path": cache_path, "existed": cache_existed},
                        output=f"{len(history) if history else 0} history entries")
        
        resolver = DataResolver(loader, cache)
        executor = CommandExecutor(resolver)

        if filtered_args:
            # Global help or Command execution
            if len(filtered_args) == 1 and filtered_args[0] in ('-h', '--help'):
                executor.print_global_help()
                return

            result = executor.find_command(filtered_args)
            if result:
                cmd, vars, is_help, remaining = result
                if is_help:
                    executor.print_help(cmd)
                else:
                    executor.execute(cmd, vars, remaining)
                cache.save()
            else:
                print("Error: Command not found.")
        else:
            # Interactive mode
            shell = InteractiveShell(resolver, executor)
            shell.run()

    class ParsedArgs:
        def __init__(self):
            self.config_override: Optional[str] = None
            self.cache_override: Optional[str] = None
            self.run_validation = False
            self.clear_cache = False
            self.clear_history = False
            self.clear_all = False
            self.set_locals_key: Optional[str] = None
            self.set_locals_value: Optional[str] = None
            self.clear_locals = False
            self.dump_cache = False
            self.filtered_args: List[str] = []
            self.should_exit = False

    def _parse_args(self, args: List[str]) -> 'ParsedArgs':
        parsed = self.ParsedArgs()
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == self.config_flag:
                if i + 1 < len(args):
                    parsed.config_override = args[i+1]
                    i += 2
                else:
                    print(f"Error: {self.config_flag} requires an argument")
                    sys.exit(1)
            elif arg == self.cache_flag:
                if i + 1 < len(args):
                    parsed.cache_override = args[i+1]
                    i += 2
                else:
                    print(f"Error: {self.cache_flag} requires an argument")
                    sys.exit(1)
            elif arg == self.validate_flag:
                parsed.run_validation = True
                i += 1
            elif arg == self.clear_cache_flag:
                parsed.clear_cache = True
                i += 1
            elif arg == self.clear_history_flag:
                parsed.clear_history = True
                i += 1
            elif arg == self.clear_all_flag:
                parsed.clear_all = True
                i += 1
            elif arg == self.set_locals_flag:
                if i + 2 < len(args):
                    parsed.set_locals_key = args[i+1]
                    parsed.set_locals_value = args[i+2]
                    i += 3
                else:
                    print(f"Error: {self.set_locals_flag} requires <key> <value>")
                    sys.exit(1)
            elif arg == self.clear_locals_flag:
                parsed.clear_locals = True
                i += 1
            elif arg == self.dump_flag:
                parsed.dump_cache = True
                i += 1
            else:
                parsed.filtered_args.append(arg)
                i += 1
        return parsed

    def _resolve_paths(self, parsed: 'ParsedArgs'):
        # Rule 1.2.6/1.2.8: New default paths in ~/.${shortcut}/ directory
        if parsed.config_override:
            final_config = os.path.expanduser(parsed.config_override)
        else:
            final_config = resolve_path(
                [f".{CUSTOM_SHORTCUT}.yaml", f"{CUSTOM_SHORTCUT}.yaml", 
                 f"~/.{CUSTOM_SHORTCUT}/{CUSTOM_SHORTCUT}.yaml"],
                f"~/.{CUSTOM_SHORTCUT}/{CUSTOM_SHORTCUT}.yaml"
            )

        if parsed.cache_override:
            final_cache = os.path.expanduser(parsed.cache_override)
        else:
            final_cache = resolve_path(
                [f".{CUSTOM_SHORTCUT}.json", f"{CUSTOM_SHORTCUT}.json", 
                 f"~/.{CUSTOM_SHORTCUT}/{CUSTOM_SHORTCUT}.json"],
                f"~/.{CUSTOM_SHORTCUT}/{CUSTOM_SHORTCUT}.json"
            )
        return final_config, final_cache

    def _handle_management_flags(self, parsed: 'ParsedArgs', cache_path: str, config_path: str = None) -> bool:
        """Returns True if execution should stop (action performed)."""
        if parsed.clear_cache or parsed.clear_history or parsed.clear_all or parsed.set_locals_key or parsed.clear_locals or parsed.dump_cache:
            import json
            from .output import get_output_strategy
            from .constants import VERBOSITY_DEFAULT
            
            # Try to load config to get verbosity setting
            verbosity = VERBOSITY_DEFAULT
            if config_path:
                try:
                    from .config import ConfigLoader
                    loader = ConfigLoader(config_path)
                    loader.load()
                    verbosity = loader.global_config.verbosity
                except Exception:
                    pass  # Config load failed - use default
            
            output = get_output_strategy(verbosity)
            
            cache = CacheManager(cache_path, True)
            try:
                cache.load()
            except Exception as e:
                # Cache load failed - non-fatal, proceed with empty cache
                print(f"Warning: Failed to load cache for management flags: {e}")
                print(f"  Action: Attempted to load cache for --{self.clear_cache_flag.lstrip('--')} or related flag")
                print(f"  Cache path: {cache_path}")
            
            if parsed.dump_cache:
                # Print decrypted cache as JSON
                print(json.dumps(cache.cache, indent=2, ensure_ascii=False))
                return True
            
            if parsed.clear_all:
                if cache.delete_all():
                    output.verbose_log(f"[VERBOSE] Cache file deleted: {cache_path}")
                    print(f"Cache file deleted: {cache_path}")
                else:
                    print(f"Cache file not found: {cache_path}")
                return True
            
            if parsed.clear_cache:
                count = cache.clear_cache()
                output.verbose_log(f"[VERBOSE] Cache modified: cleared {count} dynamic dict entries")
                print(f"Cleared {count} cache entries (history preserved)")
            
            if parsed.clear_history:
                if cache.clear_history():
                    print("Command history cleared")
                else:
                    print("No history to clear")
            
            if parsed.set_locals_key:
                cache.set_local(parsed.set_locals_key, parsed.set_locals_value)
                output.verbose_log(f"[VERBOSE] Cache modified: set _locals.{parsed.set_locals_key} = '{parsed.set_locals_value}'")
                print(f"Local variable set: {parsed.set_locals_key}={parsed.set_locals_value}")
            
            if parsed.clear_locals:
                if cache.clear_locals():
                    output.verbose_log("[VERBOSE] Cache modified: cleared all _locals")
                    print("Local variables cleared")
                else:
                    print("No local variables to clear")
            
            return True
        return False

    def _ensure_default_config(self):
        # Rules 1.1.12, 1.1.13 + SHA Enforcement
        bundled = os.path.join(os.path.dirname(__file__), f"{CUSTOM_SHORTCUT}.yaml")
        user_dir = os.path.expanduser(f"~/.{CUSTOM_SHORTCUT}")
        user_home = os.path.join(user_dir, f"{CUSTOM_SHORTCUT}.yaml")
        
        if os.path.exists(bundled):
            should_copy = False
            reason = ""
            
            if not os.path.exists(user_home):
                should_copy = True
                reason = "Missing user configuration"
            else:
                try:
                    bundled_hash = self._get_file_hash(bundled)
                    user_hash = self._get_file_hash(user_home)
                    if bundled_hash != user_hash:
                        should_copy = True
                        reason = "Configuration mismatch (SHA variation)"
                except Exception as e:
                     print(f"Warning: Failed to verify configuration integrity: {e}")

            if should_copy:
                try:
                    # Ensure directory exists before copying
                    os.makedirs(user_dir, exist_ok=True)
                    shutil.copy(bundled, user_home)
                    print(f"[{CUSTOM_NAME}] Updating default configuration from bundle: {reason}")
                except Exception as e:
                    print(f"Warning: Failed to update default configuration: {e}")

    def _get_file_hash(self, filepath: str) -> str:
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            max_chunks = 100000 
            chunks_read = 0
            while chunk := f.read(8192):
                hasher.update(chunk)
                chunks_read += 1
                if chunks_read > max_chunks:
                    raise RuntimeError(f"Config file too large or infinite read (chunks={chunks_read})")
        return hasher.hexdigest()

    def _print_app_help(self):
        print(f"\n{CUSTOM_NAME} Application Help")
        print("-" * 30)
        print("Usage Rules:")
        print("  - Configuration is defined in YAML format.")
        print("  - Supports static dicts, dynamic dicts (via shell commands), and commands.")
        print("  - Commands can use variables from user input values ${var} or dicts/dynamic_dicts $${source.key} syntax.")
        print("  - Supports persistent local variables via $${locals.key} syntax.")
        print("\nConfiguration Example:")
        print("  ---")
        print("  type: command")
        print("  name: Hello World")
        print("  alias: hello")
        print("  command: echo 'Hello World'")
        print("\nReserved Arguments:")
        # Dynamic spacing: 12 fixed + len(shortcut) to align with other flags
        help_padding = " " * (12 + len(CUSTOM_SHORTCUT))
        print(f"  -h, --help{help_padding}: Display help for commands or global help")
        print(f"  {self.config_flag} <path>      : Specify custom configuration file")
        print(f"  {self.cache_flag} <path>       : Specify custom cache file")
        print(f"  {self.validate_flag}           : Validate configuration file")
        print(f"  {self.clear_cache_flag}        : Clear dynamic dict cache (keeps history)")
        print(f"  {self.clear_history_flag}      : Clear command history")
        print(f"  {self.clear_all_flag}          : Delete entire cache file")
        print(f"  {self.set_locals_flag} <k> <v> : Set a local variable")
        print(f"  {self.clear_locals_flag}       : Clear all local variables")
        print(f"  {self.dump_flag}               : Print decrypted cache as JSON")
        print(f"  {self.dya_help_flag}               : Display this command line builder help")
        print("\nDocumentation:")
        print("  https://github.com/natanmedeiros/dynamic-alias?tab=readme-ov-file#documentation")
        print()
