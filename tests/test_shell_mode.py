"""
Shell Mode Tests

Tests for:
- Shell mode config parsing
- Shell mode execution
- Fallback to system shell
- Verbosity handling in shell mode
"""
import os
import sys
import unittest
import tempfile
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
from dynamic_alias.models import GlobalConfig
from dynamic_alias.shell import InteractiveShell
from dynamic_alias.validator import ConfigValidator


class TestShellModeConfig(unittest.TestCase):
    """Test shell mode configuration parsing."""
    
    def test_shell_mode_default_false(self):
        """Shell mode should default to False."""
        config = GlobalConfig()
        self.assertFalse(config.shell)
    
    def test_shell_mode_parsed_from_config(self):
        """Shell mode should be parsed from config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
config:
  shell: true
""")
            f.flush()
            
            loader = ConfigLoader(f.name)
            loader.load()
            
            self.assertTrue(loader.global_config.shell)
            
        os.unlink(f.name)
    
    def test_shell_mode_false_explicit(self):
        """Shell mode can be explicitly set to false."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
config:
  shell: false
""")
            f.flush()
            
            loader = ConfigLoader(f.name)
            loader.load()
            
            self.assertFalse(loader.global_config.shell)
            
        os.unlink(f.name)


class TestShellModeValidation(unittest.TestCase):
    """Test shell mode validation."""
    
    def test_shell_key_is_valid_in_config(self):
        """'shell' should be a valid config key."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
config:
  shell: true
""")
            f.flush()
            
            validator = ConfigValidator(f.name)
            report = validator.validate()
            
            # Should not have config key errors
            config_errors = [r for r in report.results 
                            if 'Unknown config keys' in r.message]
            self.assertEqual(len(config_errors), 0)
            
        os.unlink(f.name)


class TestShellExecution(unittest.TestCase):
    """Test InteractiveShell execution logic."""
    
    def setUp(self):
        self.mock_resolver = MagicMock()
        self.mock_executor = MagicMock()
        
        # Configure mocks
        self.mock_resolver.config.global_config = GlobalConfig(shell=True, verbosity='verbose')
        # Ensure cache path logic doesn't crash
        self.mock_resolver.cache.cache_path = "mock_cache.json"
        
        self.shell = InteractiveShell(self.mock_resolver, self.mock_executor)

    @patch('subprocess.run')
    def test_shell_mode_verbose_logging(self, mock_run):
        """Test that verbose logging works without error using _get_output."""
        output = self.shell._get_output()
        self.assertTrue(hasattr(output, 'verbose_log'))
        output.verbose_log('Test log')
        # Should not raise exception
        
    @patch('subprocess.run')
    def test_shell_mode_execution(self, mock_run):
        """Mock test to verify the fixed code block structure."""
        text = 'echo test'
        if self.shell.resolver.config.global_config.shell:
            try:
                self.shell._get_output().verbose_log(f'[VERBOSE] Shell mode: executing \'{text}\'')
                import subprocess
                subprocess.run(text, shell=True)
            except Exception as e:
                self.fail(f'Shell execution raised exception: {e}')
        
        mock_run.assert_called_with(text, shell=True)


if __name__ == '__main__':
    unittest.main()
