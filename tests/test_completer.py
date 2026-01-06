"""
Dynamic Alias Completer Tests
Test Rules:
    @system_rules.txt
"""
import unittest
import sys
import os
from unittest.mock import MagicMock

# Mock prompt_toolkit modules BEFORE import
sys.modules['prompt_toolkit'] = MagicMock()
sys.modules['prompt_toolkit.completion'] = MagicMock()
sys.modules['prompt_toolkit.styles'] = MagicMock()
sys.modules['prompt_toolkit.shortcuts'] = MagicMock()
sys.modules['prompt_toolkit.formatted_text'] = MagicMock()
sys.modules['prompt_toolkit.key_binding'] = MagicMock()

# Define dummy Completer class so DynamicAliasCompleter inherits correctly
class DummyCompleter:
    def get_completions(self, document, complete_event):
        pass
sys.modules['prompt_toolkit.completion'].Completer = DummyCompleter
sys.modules['prompt_toolkit.completion'].Completion = lambda text, start_position=0, display=None: (text, display)

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
        # Load actual config to test patterns
        # Assuming run from root of project
        cls.config_file = "dya.yaml"
        if not os.path.exists(cls.config_file):
             # Try looking one level up if run from tests dir (though standard is root)
             if os.path.exists(os.path.join("..", cls.config_file)):
                 cls.config_file = os.path.join("..", cls.config_file)
             else:
                 raise FileNotFoundError("dya.yaml must exist for testing")
             
        cls.loader = ConfigLoader(cls.config_file)
        cls.loader.load()
        
        # Mock Dynamic Resolver to avoid calling AWS/Redis/etc
        cls.cache = MagicMock()
        cls.cache.get.return_value = None # Force resolve if not mocked
        
        cls.resolver = DataResolver(cls.loader, cls.cache)
        
        # Pre-fill resolved_data with fake content for dynamic dicts
        cls.resolver.resolved_data = {
            'database_servers': [
                {'name': 'db1', 'host': 'h1', 'port': '5432', 'user': 'u1', 'dbname': 'd1'},
                {'name': 'db2', 'host': 'h2', 'port': '5432', 'user': 'u2', 'dbname': 'd2'}
            ],
            'redis_servers': [
                {'name': 'cache1', 'host': 'r1', 'port': '6379'},
                {'name': 'cache2', 'host': 'r2', 'port': '6379'}
            ],
            'application_servers': [
                {'name': 'app1', 'host': 'a1', 'port': '8080'},
                {'name': 'app2', 'host': 'a2', 'port': '8080'}
            ]
        }
        
        cls.executor = CommandExecutor(cls.resolver)
        cls.completer = DynamicAliasCompleter(cls.resolver, cls.executor)

    def get_completions(self, text):
        doc = MockDocument(text)
        return [c[0] for c in self.completer.get_completions(doc, None)]

    def test_01_empty_input(self):
        """Test empty input suggestions (Roots)"""
        res = self.get_completions("") 
        # Should suggest root commands: s3, check, pg, rd
        self.assertIn("pg", res)
        self.assertIn("rd", res)
        self.assertIn("check", res)
        self.assertIn("sync", res) # "s3 sync" alias starts with "sync"

    def test_02_pg_command(self):
        """Test pg command (Static root)"""
        # "pg"
        res = self.get_completions("pg") 
        self.assertIn("pg", res)
        
        # "pg " -> Suggest DBs
        res = self.get_completions("pg ")
        self.assertIn("db1", res)
        self.assertIn("db2", res)

    def test_03_pg_db_args_subs(self):
        """Test pg db1 [options] (Args and Subs)"""
        # "pg db1 " -> Suggest Args (-o, -v) and Subs (file, cmd)
        res = self.get_completions("pg db1 ")
        self.assertIn("-o", res)
        self.assertIn("-v", res)
        self.assertIn("file", res)
        self.assertIn("cmd", res)

    def test_04_pg_db_arg_value(self):
        """Test arg value hint and consumption"""
        # "pg db1 -o " -> Suggest nothing (Rule 4.18: No user var autocomplete)
        res = self.get_completions("pg db1 -o ")
        self.assertNotIn("${output_filename}", res)
        
        # "pg db1 -o my.txt " -> Resumed. Suggest -v, file, cmd. NOT -o.
        res = self.get_completions("pg db1 -o my.txt ")
        self.assertNotIn("-o", res)
        self.assertIn("-v", res)
        self.assertIn("file", res)

    def test_05_pg_db_multiple_args(self):
        """Test multiple args chaining"""
        # "pg db1 -v " -> Suggest -o, file, cmd. NOT -v.
        res = self.get_completions("pg db1 -v ")
        self.assertIn("-o", res)
        self.assertNotIn("-v", res)
        self.assertIn("file", res)
        
        # "pg db1 -v -o " -> Suggest nothing (Rule 4.18 applied to chained args)
        res = self.get_completions("pg db1 -v -o ")
        self.assertNotIn("${output_filename}", res)
        
        # "pg db1 -v -o f.txt " -> Suggest file, cmd. NOT -v, -o.
        res = self.get_completions("pg db1 -v -o f.txt ")
        self.assertNotIn("-v", res)
        self.assertNotIn("-o", res)
        self.assertIn("file", res)

    def test_06_check_app(self):
        """Test check command with app servers"""
        # "check " -> app1, app2
        res = self.get_completions("check ")
        self.assertIn("app1", res)
        self.assertIn("app2", res)

    def test_07_s3_sync(self):
        """Test s3 sync (Multi-token alias)"""
        # "sy" -> sync
        res = self.get_completions("sy")
        self.assertIn("sync", res)
        
        # "sync " -> Suggest nothing (Rule 4.20: Suppress user vars)
        res = self.get_completions("sync ")
        self.assertNotIn("${source}", res)
        
        # "sync src " -> Suggest nothing (Rule 4.20)
        res = self.get_completions("sync src ")
        self.assertNotIn("${destination}", res)

    def test_08_redis_sub(self):
        """Test redis nested sub"""
        # "rd cache1 " -> ${script} (Option) and ${script} (Sub)
        # Note: In shoco.yaml, Options and Subs overlap alias ${script}.
        res = self.get_completions("rd cache1 ")
        self.assertIn("${script}", res)
    def test_09_pg_cmd_arg(self):
        """Test pg cmd argument suppression (Rule 4.20)"""
        # "pg db1 cmd " -> Suggest nothing (Rule 4.20)
        res = self.get_completions("pg db1 cmd ")
        self.assertNotIn("${sql_text}", res)

if __name__ == '__main__':
    unittest.main()
