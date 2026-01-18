"""
Path Completion Tests

Tests for:
- path-completion config property
- System command completion from PATH
- Validation: path-completion requires shell: true
"""
import os
import sys
import unittest
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
from dynamic_alias.validator import ConfigValidator
from dynamic_alias.completer import get_system_commands


class TestPathCompletionConfig(unittest.TestCase):
    """Test path-completion config parsing."""
    
    def test_path_completion_default_false(self):
        """path_completion should default to False."""
        from dynamic_alias.models import GlobalConfig
        config = GlobalConfig()
        self.assertFalse(config.path_completion)
    
    def test_path_completion_in_config_keys(self):
        """path-completion should be in CONFIG_KEYS."""
        from dynamic_alias.constants import CONFIG_KEYS
        self.assertIn('path-completion', CONFIG_KEYS)


class TestPathCompletionValidation(unittest.TestCase):
    """Test validation of path-completion config."""
    
    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_path_completion_without_shell_fails(self):
        """path-completion: true without shell: true should fail validation."""
        config_content = """config:
  path-completion: true
---
type: command
name: Test
alias: test
command: echo test
"""
        config_path = os.path.join(self.temp_dir.name, "dya.yaml")
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        validator = ConfigValidator(config_path)
        report = validator.validate()
        
        # Should have a failure about path-completion requiring shell
        failed_messages = [r.message for r in report.results if not r.passed]
        self.assertTrue(
            any("path-completion" in msg and "shell" in msg for msg in failed_messages),
            f"Expected path-completion/shell error, got: {failed_messages}"
        )
    
    def test_path_completion_with_shell_passes(self):
        """path-completion: true with shell: true should pass validation."""
        config_content = """config:
  shell: true
  path-completion: true
---
type: command
name: Test
alias: test
command: echo test
"""
        config_path = os.path.join(self.temp_dir.name, "dya.yaml")
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        validator = ConfigValidator(config_path)
        report = validator.validate()
        
        # Should NOT have a failure about path-completion
        failed_messages = [r.message for r in report.results if not r.passed]
        self.assertFalse(
            any("path-completion" in msg for msg in failed_messages),
            f"Unexpected path-completion error: {failed_messages}"
        )


class TestGetSystemCommands(unittest.TestCase):
    """Test system command discovery from PATH."""
    
    def test_get_system_commands_returns_list(self):
        """get_system_commands should return a list."""
        # Reset cache for fresh test
        import dynamic_alias.completer as completer_module
        completer_module._system_commands_cache = None
        
        commands = get_system_commands()
        self.assertIsInstance(commands, list)
    
    def test_get_system_commands_contains_common_commands(self):
        """Should contain at least some common system commands."""
        import dynamic_alias.completer as completer_module
        completer_module._system_commands_cache = None
        
        commands = get_system_commands()
        
        # At least one common command should exist
        if os.name == 'nt':
            # Windows: should have cmd, powershell, ping, ipconfig AND built-ins like echo
            common = ['cmd', 'powershell', 'ping', 'ipconfig', 'echo', 'cls']
        else:
            # Unix: should have ls, cat, echo, grep, cd
            common = ['ls', 'cat', 'echo', 'grep', 'cd']
        
        found_any = any(cmd in commands for cmd in common)
        self.assertTrue(found_any, f"Expected at least one of {common} in commands")
        # Ensure built-in is present
        self.assertIn('echo', commands, "Built-in 'echo' not found in commands list")
    
    def test_get_system_commands_is_cached(self):
        """Second call should use cached result."""
        import dynamic_alias.completer as completer_module
        completer_module._system_commands_cache = None
        
        # First call populates cache
        result1 = get_system_commands()
        
        # Verify cache is set
        self.assertIsNotNone(completer_module._system_commands_cache)
        
        # Second call uses cache
        result2 = get_system_commands()
        
        # Should be same object (cached)
        self.assertIs(result1, result2)
    
    def test_get_system_commands_is_sorted(self):
        """Commands should be returned in sorted order."""
        import dynamic_alias.completer as completer_module
        completer_module._system_commands_cache = None
        
        commands = get_system_commands()
        
        # Should be sorted
        self.assertEqual(commands, sorted(commands))


class TestPathCompletionIntegration(unittest.TestCase):
    """Test path completion integration with completer."""
    
    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "dya.yaml")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    @patch('dynamic_alias.crypto.get_machine_id', return_value='test-machine-id')
    def test_path_completion_enabled_when_configured(self, mock_crypto):
        """path_completion should be True when configured."""
        config_content = """config:
  shell: true
  path-completion: true
---
type: command
name: Test
alias: mytest
command: echo test
"""
        with open(self.config_path, 'w') as f:
            f.write(config_content)
        
        loader = ConfigLoader(self.config_path)
        loader.load()
        
        self.assertTrue(loader.global_config.shell)
        self.assertTrue(loader.global_config.path_completion)
    
    @patch('dynamic_alias.crypto.get_machine_id', return_value='test-machine-id')
    def test_path_completion_disabled_by_default(self, mock_crypto):
        """path_completion should be False by default."""
        config_content = """config:
  shell: true
---
type: command
name: Test
alias: mytest
command: echo test
"""
        with open(self.config_path, 'w') as f:
            f.write(config_content)
        
        loader = ConfigLoader(self.config_path)
        loader.load()
        
        self.assertTrue(loader.global_config.shell)
        self.assertFalse(loader.global_config.path_completion)


if __name__ == '__main__':
    unittest.main()
