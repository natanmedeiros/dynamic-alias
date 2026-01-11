"""
Integration Tests
Test Rules:
    @system_rules.txt
    @global-test-rules.md
"""
import os
import unittest
import json
import tempfile
import sys
from unittest.mock import patch, MagicMock

# Mock prompt_toolkit modules BEFORE any imports
sys.modules['prompt_toolkit'] = MagicMock()
sys.modules['prompt_toolkit.shortcuts'] = MagicMock()
sys.modules['prompt_toolkit.formatted_text'] = MagicMock()
sys.modules['prompt_toolkit.key_binding'] = MagicMock()
sys.modules['prompt_toolkit.history'] = MagicMock()
sys.modules['prompt_toolkit.patch_stdout'] = MagicMock()
sys.modules['prompt_toolkit.completion'] = MagicMock()
sys.modules['prompt_toolkit.styles'] = MagicMock()

# Add src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dynamic_alias.config import ConfigLoader
from dynamic_alias.cache import CacheManager
from dynamic_alias.resolver import DataResolver
from dynamic_alias.executor import CommandExecutor

class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_file = os.path.join(os.path.dirname(__file__), "dya.yaml")
        assert os.path.exists(cls.config_file)
        
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "dya.json")
        
        self.loader = ConfigLoader(self.config_file)
        self.loader.load()
        
        self.cache = CacheManager(self.cache_path, enabled=True)
        self.cache.load()
        
        self.resolver = DataResolver(self.loader, self.cache)
        self.executor = CommandExecutor(self.resolver)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_strict_true(self):
        # Alias: strict (strict=true)
        chain, vars, is_help, remaining = self.executor.find_command(["strict"])
        self.assertIsNotNone(chain)
        self.assertEqual(remaining, [])
        
        # Extra args -> remaining populated
        chain, vars, is_help, remaining = self.executor.find_command(["strict", "extra"])
        self.assertEqual(remaining, ["extra"])

    def test_strict_false(self):
        # Alias: simple (strict=false default)
        chain, vars, is_help, remaining = self.executor.find_command(["simple", "extra"])
        self.assertEqual(remaining, ["extra"])

    def test_dynamic_dict_resolution(self):
        # Mock subprocess run for dynamic dicts
        with patch('dynamic_alias.resolver.subprocess.run') as mock_run:
            mock_run.return_value.stdout = '[{"id": "n1", "ip": "1.1.1.1"}]'
            mock_run.return_value.returncode = 0
            
            self.resolver.resolve_all()
            
            # Check resolved data uses mapped keys (name from id)
            nodes = self.resolver.resolved_data.get('dynamic_nodes')
            self.assertIsNotNone(nodes)
            self.assertEqual(nodes[0]['name'], 'n1')

if __name__ == '__main__':
    unittest.main()
