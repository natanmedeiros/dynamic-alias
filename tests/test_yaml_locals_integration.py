import unittest
import os
import tempfile
import shutil
import sys
from dynamic_alias.config import ConfigLoader
from dynamic_alias.cache import CacheManager
from dynamic_alias.resolver import DataResolver

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

class TestYamlLocalsIntegration(unittest.TestCase):
    def setUp(self):
        self.yaml_path = os.path.abspath("tests/dya.yaml")
        # Create temp cache file
        self.temp_dir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.temp_dir, "test_cache.json")
        
        self.loader = ConfigLoader(self.yaml_path)
        self.loader.load()
        
        self.cache = CacheManager(self.cache_path, enabled=True)
        self.cache.load() # Creates empty structure
        # Force cache enable (default logic might need checking)
        
        self.resolver = DataResolver(self.loader, self.cache)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_dynamic_dict_with_locals_real_execution(self):
        # 1. Set local variable
        local_value = "IntegrationWorks"
        self.cache.set_local("test_local_var", local_value)
        
        # 2. Resolve dynamic dict 'test_locals_dd' defined in dya.yaml
        # Command: python -c "import json; print(json.dumps([{'value': '$${locals.test_local_var}'}]))"
        
        # Resolve
        result = self.resolver.resolve_one("test_locals_dd")
        
        # 3. Verify result
        # The dynamic dict maps 'value' (from json) to 'result' (internal key)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0, "Result list shouldn't be empty")
        
        first_item = result[0]
        self.assertIn('result', first_item)
        self.assertEqual(first_item['result'], local_value)

if __name__ == '__main__':
    unittest.main()
