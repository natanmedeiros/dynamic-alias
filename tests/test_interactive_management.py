"""
Interactive Mode Management Commands Tests

Tests for management commands in interactive mode:
- --${shortcut}-clear-cache
- --${shortcut}-clear-history
- --${shortcut}-clear-all
- --${shortcut}-clear-locals
- --${shortcut}-set-locals
- --${shortcut}-dump

Also tests that config/cache path flags are NOT supported in interactive mode.
"""
import os
import sys
import unittest
import tempfile
import json
from unittest.mock import MagicMock, patch
from io import StringIO

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

from dynamic_alias.cache import CacheManager
from dynamic_alias.shell import InteractiveShell
from dynamic_alias.resolver import DataResolver
from dynamic_alias.executor import CommandExecutor
from dynamic_alias.config import ConfigLoader
from dynamic_alias.constants import CUSTOM_SHORTCUT


class TestInteractiveManagementCommands(unittest.TestCase):
    """Test management commands work in interactive mode."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        self.config_path = os.path.join(self.temp_dir.name, "config.yaml")
        
        # Create minimal config
        with open(self.config_path, 'w') as f:
            f.write("config:\n  history-size: 5\n")
        
        self.loader = ConfigLoader(self.config_path)
        self.loader.load()
        
        self.cache = CacheManager(self.cache_path, enabled=True)
        self.resolver = DataResolver(self.loader, self.cache)
        self.executor = CommandExecutor(self.resolver)
        self.shell = InteractiveShell(self.resolver, self.executor)
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_clear_cache_in_interactive(self):
        """--${shortcut}-clear-cache should work in interactive mode."""
        # Setup cache with some data
        self.cache.set("dynamic_dict", [{"id": 1}])
        self.cache.add_history("cmd1")
        self.cache.save()
        
        # Execute the management command
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.shell._handle_interactive_management([f"--{CUSTOM_SHORTCUT}-clear-cache"])
        
        self.assertTrue(result)
        self.assertNotIn("dynamic_dict", self.cache.cache)
        self.assertIn("_history", self.cache.cache)  # History preserved
    
    def test_clear_history_in_interactive(self):
        """--${shortcut}-clear-history should work in interactive mode."""
        self.cache.add_history("cmd1")
        self.cache.add_history("cmd2")
        self.cache.save()
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.shell._handle_interactive_management([f"--{CUSTOM_SHORTCUT}-clear-history"])
        
        self.assertTrue(result)
        self.assertEqual(self.cache.get_history(), [])
    
    def test_clear_all_in_interactive(self):
        """--${shortcut}-clear-all should work in interactive mode."""
        self.cache.add_history("cmd1")
        self.cache.save()
        self.assertTrue(os.path.exists(self.cache_path))
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.shell._handle_interactive_management([f"--{CUSTOM_SHORTCUT}-clear-all"])
        
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.cache_path))
    
    def test_clear_locals_in_interactive(self):
        """--${shortcut}-clear-locals should work in interactive mode."""
        self.cache.set_local("key1", "value1")
        self.cache.set_local("key2", "value2")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.shell._handle_interactive_management([f"--{CUSTOM_SHORTCUT}-clear-locals"])
        
        self.assertTrue(result)
        self.assertEqual(self.cache.get_locals(), {})
    
    def test_set_locals_in_interactive(self):
        """--${shortcut}-set-locals should work in interactive mode."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.shell._handle_interactive_management([f"--{CUSTOM_SHORTCUT}-set-locals", "mykey", "myvalue"])
        
        self.assertTrue(result)
        self.assertEqual(self.cache.get_local("mykey"), "myvalue")
    
    def test_set_locals_missing_args(self):
        """--${shortcut}-set-locals should error if missing arguments."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.shell._handle_interactive_management([f"--{CUSTOM_SHORTCUT}-set-locals", "key_only"])
        
        self.assertTrue(result)
        self.assertIn("requires", mock_stdout.getvalue())
    
    def test_dump_in_interactive(self):
        """--${shortcut}-dump should print decrypted cache as JSON."""
        self.cache.set_local("key", "value")
        self.cache.add_history("cmd1")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.shell._handle_interactive_management([f"--{CUSTOM_SHORTCUT}-dump"])
        
        self.assertTrue(result)
        output = mock_stdout.getvalue()
        # Should be valid JSON
        parsed = json.loads(output)
        self.assertEqual(parsed["_locals"]["key"], "value")
        self.assertIn("cmd1", parsed["_history"])


class TestInteractiveUnsupportedFlags(unittest.TestCase):
    """Test that config/cache path flags are NOT supported in interactive mode."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        self.config_path = os.path.join(self.temp_dir.name, "config.yaml")
        
        with open(self.config_path, 'w') as f:
            f.write("config:\n  history-size: 5\n")
        
        self.loader = ConfigLoader(self.config_path)
        self.loader.load()
        
        self.cache = CacheManager(self.cache_path, enabled=True)
        self.resolver = DataResolver(self.loader, self.cache)
        self.executor = CommandExecutor(self.resolver)
        self.shell = InteractiveShell(self.resolver, self.executor)
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_config_flag_not_supported(self):
        """--${shortcut}-config should NOT be supported in interactive mode."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.shell._handle_interactive_management([f"--{CUSTOM_SHORTCUT}-config", "/some/path"])
        
        self.assertTrue(result)  # Handled (blocked)
        output = mock_stdout.getvalue()
        self.assertIn("not supported in interactive mode", output)
    
    def test_cache_flag_not_supported(self):
        """--${shortcut}-cache should NOT be supported in interactive mode."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.shell._handle_interactive_management([f"--{CUSTOM_SHORTCUT}-cache", "/some/path"])
        
        self.assertTrue(result)  # Handled (blocked)
        output = mock_stdout.getvalue()
        self.assertIn("not supported in interactive mode", output)
    
    def test_normal_commands_pass_through(self):
        """Normal commands should not be handled by management handler."""
        result = self.shell._handle_interactive_management(["my-command", "arg1"])
        self.assertFalse(result)  # Not handled - should be passed to normal command processing


class TestDumpFlag(unittest.TestCase):
    """Test the --${shortcut}-dump flag in non-interactive mode."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        self.config_path = os.path.join(self.temp_dir.name, "config.yaml")
        
        with open(self.config_path, 'w') as f:
            f.write("config:\n  history-size: 5\n")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_dump_flag_outputs_json(self):
        """--${shortcut}-dump should output decrypted cache as JSON."""
        # Setup encrypted cache
        cache = CacheManager(self.cache_path, enabled=True)
        cache.set_local("test_key", "test_value")
        cache.add_history("test_cmd")
        cache.save()
        
        # Import cli after mocks are set
        from dynamic_alias.cli import DynamicAliasCLI
        
        cli = DynamicAliasCLI()
        
        # Parse args
        parsed = cli._parse_args([f"--{CUSTOM_SHORTCUT}-dump"])
        self.assertTrue(parsed.dump_cache)
        
        # Execute management flags
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = cli._handle_management_flags(parsed, self.cache_path)
        
        self.assertTrue(result)
        output = mock_stdout.getvalue()
        
        # Verify JSON output
        parsed_output = json.loads(output)
        self.assertEqual(parsed_output["_locals"]["test_key"], "test_value")
        self.assertIn("test_cmd", parsed_output["_history"])


if __name__ == '__main__':
    unittest.main()
