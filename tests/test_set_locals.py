"""
Tests for Rule 4.21: set-locals in commands.
"""
import os
import sys
import unittest
import json
from unittest.mock import MagicMock, patch

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

from dynamic_alias.executor import CommandExecutor
from dynamic_alias.models import CommandConfig


class TestSetLocals(unittest.TestCase):
    """Test Rule 4.21: Capture command output as locals."""
    
    def setUp(self):
        self.mock_resolver = MagicMock()
        self.mock_cache = MagicMock()
        self.mock_resolver.cache = self.mock_cache
        self.executor = CommandExecutor(self.mock_resolver)
    
    @patch('dynamic_alias.executor.subprocess.run')
    def test_set_locals_valid_json(self, mock_run):
        """Should set locals from valid JSON output when set-locals is true."""
        # Setup mock command
        cmd_config = CommandConfig(
            name="Test",
            alias="test",
            command="echo json",
            set_locals=True
        )
        
        # Setup mock subprocess result
        mock_result = MagicMock()
        mock_result.stdout = '{"key1": "value1", "key2": "value2"}'
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Execute
        self.executor.execute([cmd_config], {})
        
        # Verify
        mock_run.assert_called_with(
            "echo json", 
            shell=True, 
            timeout=None, 
            capture_output=True, 
            text=True
        )
        self.mock_cache.set_local.assert_any_call("key1", "value1")
        self.mock_cache.set_local.assert_any_call("key2", "value2")
        self.mock_cache.save.assert_called()

    @patch('dynamic_alias.executor._run_interactive_subprocess')
    def test_set_locals_disabled(self, mock_run):
        """Should NOT capture output when set-locals is false."""
        cmd_config = CommandConfig(
            name="Test",
            alias="test",
            command="echo json",
            set_locals=False
        )
        
        self.executor.execute([cmd_config], {})
        
        # Verify _run_interactive_subprocess was called (not subprocess.run with capture_output)
        mock_run.assert_called()
        args, kwargs = mock_run.call_args
        # Should be called with command string, not capture_output
        self.assertIn("echo json", args[0])
        self.mock_cache.set_local.assert_not_called()

    @patch('dynamic_alias.executor.subprocess.run')
    def test_set_locals_invalid_json(self, mock_run):
        """Should handle invalid JSON gracefully (print error, no crash)."""
        cmd_config = CommandConfig(
            name="Test",
            alias="test",
            command="echo bad",
            set_locals=True
        )
        
        mock_result = MagicMock()
        mock_result.stdout = 'not valid json'
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Should not raise exception
        self.executor.execute([cmd_config], {})
        
        self.mock_cache.set_local.assert_not_called()

    @patch('dynamic_alias.executor.subprocess.run')
    def test_set_locals_not_dict(self, mock_run):
        """Should error if JSON is a list, not a dict."""
        cmd_config = CommandConfig(
            name="Test",
            alias="test",
            command="echo list",
            set_locals=True
        )
        
        mock_result = MagicMock()
        mock_result.stdout = '[{"key": "value"}]'
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        self.executor.execute([cmd_config], {})
        
        self.mock_cache.set_local.assert_not_called()

if __name__ == '__main__':
    unittest.main()
