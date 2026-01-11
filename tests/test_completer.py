"""
Dynamic Alias Completer Tests
Test Rules:
    @system_rules.txt
    @global-test-rules.md
"""
import unittest
import sys
import os
from unittest.mock import MagicMock

# Mocks are centralized in conftest.py

# Add src to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dynamic_alias.completer import DynamicAliasCompleter
from dynamic_alias.config import ConfigLoader
from dynamic_alias.resolver import DataResolver
from dynamic_alias.executor import CommandExecutor

class MockDocument:
    def __init__(self, text):
        self.text_before_cursor = text

class TestDynamicAliasCompleter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # use dedicated test config fixture
        cls.config_file = os.path.join(os.path.dirname(__file__), "dya.yaml")
        if not os.path.exists(cls.config_file):
             raise FileNotFoundError(f"{cls.config_file} must exist for testing")
             
        cls.loader = ConfigLoader(cls.config_file)
        cls.loader.load()
        
        # Mock Dynamic Resolver to avoid calling AWS/Redis/etc
        cls.cache = MagicMock()
        cls.cache.get.return_value = None # Force resolve if not mocked
        
        cls.resolver = DataResolver(cls.loader, cls.cache)
        
        # Pre-fill resolved_data with fake content for dynamic dicts matching dya.yaml
        cls.resolver.resolved_data = {
            'static_envs': [
                {'name': 'dev', 'url': 'dev.internal'},
                {'name': 'prod', 'url': 'prod.internal'}
            ],
            'dynamic_nodes': [
                {'name': 'node-1', 'ip': '10.0.0.1'},
                {'name': 'node-2', 'ip': '10.0.0.2'}
            ],
            'cached_items': [
                {'name': 'item-1'}
            ]
        }
        
        cls.executor = CommandExecutor(cls.resolver)
        cls.completer = DynamicAliasCompleter(cls.resolver, cls.executor)

    def get_completions(self, text):
        doc = MockDocument(text)
        return [c.text for c in self.completer.get_completions(doc, None)]

    def test_01_empty_input(self):
        """Test empty input suggestions (Roots)"""
        res = self.get_completions("") 
        # Should suggest root commands from dya.yaml
        self.assertIn("simple", res)
        self.assertIn("consume", res)
        self.assertIn("dyn", res)
        self.assertIn("complex", res)
        self.assertIn("strict", res)
        self.assertIn("timeout", res)

    def test_02_simple_alias(self):
        """Test simple alias"""
        res = self.get_completions("simple") 
        self.assertIn("simple", res)
        
    def test_03_dict_consumer(self):
        """Test consume $${static_envs.name}"""
        # "consume " -> Suggest envs
        res = self.get_completions("consume ")
        self.assertIn("dev", res)
        self.assertIn("prod", res)

    def test_04_complex_structure(self):
        """Test complex structure (args in root)"""
        # "complex " -> Suggest nothing (user var ${arg1})
        # Rule 4.20 suppress user var
        res = self.get_completions("complex ")
        self.assertNotIn("${arg1}", res)

    def test_05_complex_args(self):
        """Test complex args after var"""
        # "complex val " -> Suggest --flag, --opt, sub1
        res = self.get_completions("complex val ")
        self.assertIn("--flag", res)
        self.assertIn("--opt", res)
        self.assertIn("sub1", res)

    def test_06_complex_sub(self):
        """Test recursive sub"""
        # "complex val sub1 " -> Suggest deep
        res = self.get_completions("complex val sub1 ")
        self.assertIn("deep", res)

    def test_07_dynamic_consumer(self):
        """Test dyn $${dynamic_nodes.name}"""
        res = self.get_completions("dyn ")
        self.assertIn("node-1", res)
        self.assertIn("node-2", res)

    def test_08_complex_arg_value(self):
        """Test arg with user var value"""
        # "complex val --opt " -> suppress ${val}
        res = self.get_completions("complex val --opt ")
        self.assertNotIn("${val}", res)
        
        # "complex val --opt 123 " -> Resumed, suggest --flag, sub1 (not --opt)
        res = self.get_completions("complex val --opt 123 ")
        self.assertIn("--flag", res)
        self.assertIn("sub1", res)
        self.assertNotIn("--opt", res)

if __name__ == '__main__':
    unittest.main()
