import os
import sys
import unittest
import tempfile
import json
from unittest.mock import MagicMock, patch

# Import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dynamic_alias.cache import CacheManager
from dynamic_alias.shell import InteractiveShell
from dynamic_alias.resolver import DataResolver
from dynamic_alias.executor import CommandExecutor
from dynamic_alias.config import ConfigLoader

class TestShellSync(unittest.TestCase):
    """Test that Shell synchronization logic works (picking up external changes)."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        self.config_path = os.path.join(self.temp_dir.name, "config.yaml")
        
        # Create dummy config
        with open(self.config_path, 'w') as f:
            f.write("config:\n  history-size: 5\n")
            
        self.loader = ConfigLoader(self.config_path)
        self.loader.load()
        
    def tearDown(self):
        self.temp_dir.cleanup()
        
    def test_run_loop_syncs_cache(self):
        """InteractiveShell.run should reload cache before saving history."""
        from dynamic_alias.crypto import encrypt_data
        from dynamic_alias.constants import CACHE_KEY_CRYPT
        
        # 1. Setup initial cache state
        cache = CacheManager(self.cache_path, enabled=True)
        cache.set_local('key', 'initial')
        
        resolver = DataResolver(self.loader, cache)
        executor = CommandExecutor(resolver)
        shell = InteractiveShell(resolver, executor)
        
        # 2. Simulate external process changing the file (encrypted)
        external_data = {
            '_locals': {'key': 'updated_by_subprocess'},
            '_history': ['initial_cmd']
        }
        encrypted = encrypt_data(external_data)
        with open(self.cache_path, 'w') as f:
            json.dump({CACHE_KEY_CRYPT: encrypted}, f)
            
        # 3. Mock PromptSession and related
        with patch('dynamic_alias.shell.PromptSession') as MockSession, \
             patch('dynamic_alias.shell.DynamicAliasCompleter'), \
             patch('sys.exit'): # Prevent exit

            session_instance = MockSession.return_value
            # return "new_command" once, then "exit"
            session_instance.prompt.side_effect = ["new_command", "exit"]
            
            # Run shell
            shell.run()
            
        # 4. Verify internal cache state is updated (InMemory check)
        # The cache object in shell.resolver.cache should have the new value
        self.assertEqual(resolver.cache.get_local('key'), 'updated_by_subprocess')
        
        # 5. Verify file contains merged state (reload via CacheManager)
        reload_cache = CacheManager(self.cache_path, enabled=True)
        reload_cache.load()
            
        self.assertEqual(reload_cache.get_local('key'), 'updated_by_subprocess')
        self.assertIn('new_command', reload_cache.get_history())
        self.assertIn('initial_cmd', reload_cache.get_history())

if __name__ == "__main__":
    unittest.main()
