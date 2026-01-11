"""
Timeout Tests
Test Rules:
    @system_rules.txt
    @global-test-rules.md
"""
import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dynamic_alias.executor import CommandExecutor
from dynamic_alias.resolver import DataResolver
from dynamic_alias.config import ConfigLoader

class TestTimeout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_file = os.path.join(os.path.dirname(__file__), "dya.yaml")
        assert os.path.exists(cls.config_file)
        
    def setUp(self):
        self.loader = ConfigLoader(self.config_file)
        self.loader.load()
        self.resolver = DataResolver(self.loader, MagicMock())
        self.executor = CommandExecutor(self.resolver)

    @patch('dynamic_alias.executor.print_formatted_text')
    @patch('subprocess.run')
    def test_command_timeout_from_config(self, mock_run, mock_print):
        # 1. Custom Timeout (Timeout Cmd -> timeout: 10)
        # Find 'timeout' command
        chain, vars, is_help, remaining = self.executor.find_command(["timeout"])
        assert chain is not None
        
        self.executor.execute(chain, vars, remaining)
        args, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get('timeout'), 10)

    @patch('subprocess.run')
    def test_dynamic_dict_timeout(self, mock_run):
        # Setup mock return valid json
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '[{"id": "test"}]'

        # 1. Default Timeout (dynamic_nodes has no timeout specified, default 10?)
        # Models default is 10.
        dd_config = self.loader.dynamic_dicts.get('dynamic_nodes')
        # dya.yaml: no timeout specified for dynamic_nodes.
        # So it should be default.
        
        self.resolver._execute_dynamic_source(dd_config)
        args, kwargs = mock_run.call_args
        # Default is 10 in DynamicDictConfig?
        # Let's check model... usually it's 10.
        self.assertEqual(kwargs.get('timeout'), 10) 

if __name__ == '__main__':
    unittest.main()
