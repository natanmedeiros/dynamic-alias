"""
History Integration Tests
Test Rules:
    @system_rules.txt
    @global-test-rules.md

Tests verify history behavior with REAL persistence to tests/dya.json:
- If _history doesn't exist, create it
- If exists, append
- When exceeds limit, shift (remove oldest)
"""
import unittest
import os
import json
import sys
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Mocks are centralized in conftest.py

from dynamic_alias.cache import CacheManager
from dynamic_alias.config import ConfigLoader
from dynamic_alias.resolver import DataResolver
from dynamic_alias.executor import CommandExecutor
from dynamic_alias.shell import CacheHistory

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DYA_YAML_PATH = os.path.join(TEST_DIR, "dya.yaml")
DYA_JSON_PATH = os.path.join(TEST_DIR, "dya.json")

class TestHistoryIntegration(unittest.TestCase):
    """
    Integration tests that verify history persistence to tests/dya.json
    Each test run adds to real history (no backup/restore)
    """
    
    def setUp(self):
        # Load config from tests/dya.yaml
        self.loader = ConfigLoader(DYA_YAML_PATH)
        self.loader.load()
        
        # Use tests/dya.json as cache file (per Global Test Rules)
        self.cache = CacheManager(DYA_JSON_PATH, enabled=True)
        self.cache.load()
        
        self.resolver = DataResolver(self.loader, self.cache)
        self.executor = CommandExecutor(self.resolver)
        
        # Get history limit from config (should be 5 from dya.yaml)
        self.history_limit = self.loader.global_config.history_size
        
        # History adapter like shell uses
        self.history_adapter = CacheHistory(self.cache, self.history_limit)
    
    def test_history_create_if_not_exists(self):
        """Test: If _history doesn't exist, create it"""
        # Get current state
        had_history = '_history' in self.cache.cache
        initial_len = len(self.cache.get_history())
        
        # Add a command
        self.history_adapter.store_string("test_create")
        
        # Verify _history exists and has at least one entry
        history = self.cache.get_history()
        self.assertGreater(len(history), 0)
        self.assertIn("test_create", history)
        
        # Verify persisted to file
        with open(DYA_JSON_PATH, 'r') as f:
            data = json.load(f)
        self.assertIn('_history', data)
    
    def test_history_append(self):
        """Test: Append to existing history"""
        initial_history = self.cache.get_history().copy()
        initial_len = len(initial_history)
        
        # Add new command
        new_cmd = f"test_append_{initial_len}"
        self.history_adapter.store_string(new_cmd)
        
        # Verify appended
        new_history = self.cache.get_history()
        self.assertEqual(new_history[-1], new_cmd)
        
        # If not at limit, length should increase
        if initial_len < self.history_limit:
            self.assertEqual(len(new_history), initial_len + 1)
    
    def test_history_shift_when_exceeds_limit(self):
        """Test: When history exceeds limit, shift (remove oldest)"""
        # Fill history to limit
        for i in range(self.history_limit + 2):
            self.history_adapter.store_string(f"shift_test_{i}")
        
        # Verify length never exceeds limit
        history = self.cache.get_history()
        self.assertLessEqual(len(history), self.history_limit)
        
        # Oldest should have been removed
        self.assertNotIn("shift_test_0", history)
        self.assertNotIn("shift_test_1", history)
        
        # Most recent should be present
        self.assertIn(f"shift_test_{self.history_limit + 1}", history)
    
    def test_history_persists_across_sessions(self):
        """Test: History persists in tests/dya.json across cache reloads"""
        # Add a unique command
        unique_cmd = f"persist_test_{os.getpid()}"
        self.history_adapter.store_string(unique_cmd)
        
        # Create new cache manager (simulates new session)
        new_cache = CacheManager(DYA_JSON_PATH, enabled=True)
        new_cache.load()
        
        # Verify command persisted
        loaded_history = new_cache.get_history()
        self.assertIn(unique_cmd, loaded_history)
    
    def test_load_history_strings_reversed(self):
        """Test: load_history_strings returns reversed order for up-arrow"""
        # Add commands in order
        self.history_adapter.store_string("order_first")
        self.history_adapter.store_string("order_second")
        
        # Load via adapter (should be reversed: newest first)
        loaded = list(self.history_adapter.load_history_strings())
        
        # Find positions
        first_idx = loaded.index("order_first") if "order_first" in loaded else -1
        second_idx = loaded.index("order_second") if "order_second" in loaded else -1
        
        # Second (newer) should come before first in reversed list
        self.assertLess(second_idx, first_idx)
    
    def test_history_no_ttl_metadata(self):
        """Test: _history is plain list of strings (no timestamps like dynamic dicts)"""
        self.history_adapter.store_string("no_ttl_test")
        
        with open(DYA_JSON_PATH, 'r') as f:
            data = json.load(f)
        
        # _history should be list of strings
        self.assertIsInstance(data['_history'], list)
        for item in data['_history']:
            self.assertIsInstance(item, str)
            self.assertNotIsInstance(item, dict)

if __name__ == '__main__':
    unittest.main()
