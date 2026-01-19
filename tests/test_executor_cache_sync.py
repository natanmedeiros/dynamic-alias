"""
Test for cache synchronization after subprocess execution.

This test validates the fix for the race condition where:
1. Parent process saves cache before executing subprocess
2. Subprocess modifies cache (e.g., set-locals)
3. Parent reloads cache AFTER subprocess to pick up changes
4. Parent then saves merged state

Without the fix, the parent would overwrite subprocess changes.
"""
import os
import sys
import unittest
import tempfile
import json
from unittest.mock import MagicMock, patch

# Import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dynamic_alias.cache import CacheManager
from dynamic_alias.executor import CommandExecutor
from dynamic_alias.resolver import DataResolver
from dynamic_alias.config import ConfigLoader


class TestExecutorCacheSync(unittest.TestCase):
    """Test that executor.execute properly syncs cache after subprocess runs."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        self.config_path = os.path.join(self.temp_dir.name, "config.yaml")
        
        # Create dummy config with a simple command
        with open(self.config_path, 'w') as f:
            f.write("""config:
  history-size: 5
---
type: command
name: Test Command
alias: test-cmd
command: echo test
""")
            
        self.loader = ConfigLoader(self.config_path)
        self.loader.load()
        
    def tearDown(self):
        self.temp_dir.cleanup()
        
    @patch('dynamic_alias.crypto.get_machine_id', return_value='test-machine-id')
    def test_execute_reloads_cache_after_subprocess(self, mock_machine_id):
        """Executor should reload cache after subprocess to pick up external changes."""
        from dynamic_alias.crypto import encrypt_data, decrypt_data
        from dynamic_alias.constants import CACHE_KEY_CRYPT
        
        # 1. Setup initial cache
        cache = CacheManager(self.cache_path, enabled=True)
        cache.set_local('key', 'initial')
        
        resolver = DataResolver(self.loader, cache)
        executor = CommandExecutor(resolver)
        
        # 2. Find the test command
        result = executor.find_command(['test-cmd'])
        self.assertIsNotNone(result)
        cmd_chain, variables, is_help, remaining = result
        
        # 3. Create a mock for subprocess.run that simulates external modification
        original_subprocess_run = __import__('subprocess').run
        
        def mock_subprocess_run(*args, **kwargs):
            # Simulate subprocess modifying the cache file (handling encryption)
            with open(self.cache_path, 'r') as f:
                raw = json.load(f)
            # Decrypt, modify, encrypt
            data = decrypt_data(raw[CACHE_KEY_CRYPT])
            data['_locals']['key'] = 'modified_by_subprocess'
            encrypted = encrypt_data(data)
            with open(self.cache_path, 'w') as f:
                json.dump({CACHE_KEY_CRYPT: encrypted}, f)
            return MagicMock(returncode=0)
        
        # 4. Execute with mocked subprocess
        with patch('dynamic_alias.executor._run_interactive_subprocess', side_effect=mock_subprocess_run):
            executor.execute(cmd_chain, variables, remaining)
        
        # 5. Verify in-memory cache has the subprocess value
        self.assertEqual(cache.get_local('key'), 'modified_by_subprocess')
        
        # 6. Verify disk file also has the value (wasn't overwritten)
        reload_cache = CacheManager(self.cache_path, enabled=True)
        reload_cache.load()
        self.assertEqual(reload_cache.get_local('key'), 'modified_by_subprocess')


if __name__ == "__main__":
    unittest.main()
