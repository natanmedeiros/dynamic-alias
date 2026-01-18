"""
Tests for locals substitution in DynamicDict commands.
"""
import unittest
import json
from unittest.mock import MagicMock, patch
from dynamic_alias.resolver import DataResolver
from dynamic_alias.models import DynamicDictConfig, GlobalConfig

class TestDynamicDictLocals(unittest.TestCase):
    
    def setUp(self):
        self.mock_config_loader = MagicMock()
        self.mock_config_loader.global_config = GlobalConfig()
        self.mock_config_loader.dicts = {}
        self.mock_config_loader.dynamic_dicts = {}
        
        self.mock_cache = MagicMock()
        # Setup locals: "testkey" -> "resolved_value"
        # Note: key must match \w+ regex (no hyphens) for now as per current constants.py
        self.mock_cache.get_local.side_effect = lambda k: "resolved_value" if k == "testkey" else None
        
        self.resolver = DataResolver(self.mock_config_loader, self.mock_cache)
        
    @patch('subprocess.run')
    def test_dynamic_dict_command_resolves_locals(self, mock_subprocess):
        """
        Verify that $${locals.key} is substituted in dynamic_dict command 
        before execution.
        """
        # Mock successful subprocess execution returning valid JSON
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = json.dumps([{"key": "value"}])
        mock_subprocess.return_value = mock_process
        
        # Define dynamic dict command using local variable
        # Command: echo $${locals.testkey}
        dd_config = DynamicDictConfig(
            name="test_dynamic",
            command='echo $${locals.testkey}',
            mapping={'res': 'key'}
        )
        
        # Execute
        self.resolver._execute_dynamic_source(dd_config)
        
        # Verify substitution
        # Expected: echo resolved_value
        expected_cmd = "echo resolved_value"
        
        self.assertTrue(mock_subprocess.called)
        actual_cmd = mock_subprocess.call_args[0][0]
        
        self.assertEqual(actual_cmd, expected_cmd, 
                         f"Locals not resolved. Got: '{actual_cmd}'")

if __name__ == '__main__':
    unittest.main()
