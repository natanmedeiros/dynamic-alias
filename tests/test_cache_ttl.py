"""
Cache TTL Tests
Test Rules:
    @system_rules.txt
    @global-test-rules.md
"""
import unittest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

# Add src to path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Mocks are centralized in conftest.py

from dynamic_alias.cache import CacheManager
from dynamic_alias.models import DynamicDictConfig
from dynamic_alias.resolver import DataResolver
from dynamic_alias.config import ConfigLoader

class TestCacheTTL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_file = os.path.join(os.path.dirname(__file__), "dya.yaml")
        assert os.path.exists(cls.config_file)
        
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = os.path.join(self.temp_dir.name, "dya.json")
        
        self.loader = ConfigLoader(self.config_file)
        self.loader.load()
        
        self.cache_manager = CacheManager(self.cache_file, enabled=True)
        self.resolver = DataResolver(self.loader, self.cache_manager)
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cache_ttl_config_parsing(self):
        # Verify dya.yaml 'cached_items' has cache-ttl: 2
        dd_config = self.loader.dynamic_dicts.get('cached_items')
        assert dd_config is not None
        assert dd_config.cache_ttl == 2

    def test_cache_stores_with_timestamp(self):
        # Mock subprocess.run 
        with patch('dynamic_alias.resolver.subprocess.run') as mock_run:
            mock_run.return_value.stdout = '[{"id": "item1"}]'
            mock_run.return_value.returncode = 0
            
            self.resolver.resolve_all()
            
            # Save cache to file
            self.cache_manager.save()
            
            # Check cache file content - should have timestamp
            with open(self.cache_file, 'r') as f:
                cache_content = json.load(f)
                assert 'cached_items' in cache_content
                assert 'timestamp' in cache_content['cached_items']
                assert 'data' in cache_content['cached_items']

if __name__ == '__main__':
    unittest.main()
