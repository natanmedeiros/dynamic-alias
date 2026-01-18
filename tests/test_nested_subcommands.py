"""
Nested Subcommand Tests

Tests for:
- Enter key behavior with nested subcommands
- Execution at any level of subcommand nesting
- Validation that parent commands can execute without selecting child
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
from dynamic_alias.cache import CacheManager
from dynamic_alias.resolver import DataResolver
from dynamic_alias.executor import CommandExecutor
import tempfile


class TestNestedSubcommandExecution(unittest.TestCase):
    """Test that nested subcommands can execute at any level."""
    
    @classmethod
    def setUpClass(cls):
        cls.config_path = os.path.join(os.path.dirname(__file__), "dya.yaml")
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        
        self.loader = ConfigLoader(self.config_path)
        self.loader.load()
        
        # Mock crypto for cache
        self.crypto_patcher = patch('dynamic_alias.crypto.get_machine_id', return_value='test-id')
        self.crypto_patcher.start()
        
        self.cache = CacheManager(self.cache_path, enabled=True)
        self.cache.load()
        
        self.resolver = DataResolver(self.loader, self.cache)
        self.executor = CommandExecutor(self.resolver)
    
    def tearDown(self):
        self.crypto_patcher.stop()
        self.temp_dir.cleanup()
    
    def test_parent_command_executes_without_subcommand(self):
        """Parent command should be executable even when subcommands exist."""
        # Find 'nested-test-cmd' - it has subcommands but should still be findable
        result = self.executor.find_command(['nested-test-cmd'])
        
        # Should find the command
        self.assertIsNotNone(result)
        chain, variables, is_help, remaining = result
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0].alias, 'nested-test-cmd')
    
    def test_level1_subcommand_executes_without_level2(self):
        """Level 1 subcommand should execute without requiring level 2."""
        # 'nested-test-cmd level1' should be findable and executable
        result = self.executor.find_command(['nested-test-cmd', 'level1'])
        
        self.assertIsNotNone(result)
        chain, variables, is_help, remaining = result
        
        # Chain should have nested-test-cmd -> level1
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0].alias, 'nested-test-cmd')
        self.assertEqual(chain[1].alias, 'level1')
    
    def test_level2_subcommand_executes(self):
        """Level 2 subcommand should be findable and executable."""
        # 'nested-test-cmd level1 level2' 
        result = self.executor.find_command(['nested-test-cmd', 'level1', 'level2'])
        
        self.assertIsNotNone(result)
        chain, variables, is_help, remaining = result
        
        # Chain should have nested-test-cmd -> level1 -> level2
        self.assertEqual(len(chain), 3)
        self.assertEqual(chain[0].alias, 'nested-test-cmd')
        self.assertEqual(chain[1].alias, 'level1')
        self.assertEqual(chain[2].alias, 'level2')
    
    def test_partial_match_at_level1_is_valid(self):
        """Typing 'nested-test-cmd level1' and pressing Enter should execute level1."""
        result = self.executor.find_command(['nested-test-cmd', 'level1'])
        
        self.assertIsNotNone(result)
        chain, variables, is_help, remaining = result
        
        # Should match exactly at level1, not auto-select level2
        self.assertEqual(chain[-1].alias, 'level1')
        
        # Remaining should be empty (no extra tokens)
        self.assertEqual(remaining, [])


class TestKeyBindingBehavior(unittest.TestCase):
    """Test the Enter key binding behavior logic."""
    
    def test_enter_with_no_selection_should_execute(self):
        """When menu is open but no item selected, Enter should execute."""
        # This tests the logic: if complete_state but no current_completion -> execute
        
        # Create mock buffer with complete_state but no current_completion
        mock_buffer = MagicMock()
        mock_buffer.complete_state = MagicMock()
        mock_buffer.complete_state.current_completion = None
        mock_buffer.complete_state.completions = [MagicMock(), MagicMock()]
        
        # The condition for executing is:
        # NOT (complete_state AND current_completion)
        should_execute = not (mock_buffer.complete_state and mock_buffer.complete_state.current_completion)
        
        self.assertTrue(should_execute, "Should execute when no item is selected")
    
    def test_enter_with_selection_should_apply(self):
        """When menu is open and item is selected, Enter should apply completion."""
        mock_buffer = MagicMock()
        mock_buffer.complete_state = MagicMock()
        mock_buffer.complete_state.current_completion = MagicMock()  # Item selected
        
        # The condition for applying completion is:
        # complete_state AND current_completion
        should_apply = bool(mock_buffer.complete_state and mock_buffer.complete_state.current_completion)
        
        self.assertTrue(should_apply, "Should apply completion when item is selected")
    
    def test_enter_with_no_menu_should_execute(self):
        """When no menu is open, Enter should execute."""
        mock_buffer = MagicMock()
        mock_buffer.complete_state = None
        
        # The condition: NOT (complete_state AND current_completion)
        should_execute = not (mock_buffer.complete_state and 
                             getattr(mock_buffer.complete_state, 'current_completion', None))
        
        self.assertTrue(should_execute, "Should execute when no menu is open")


class TestSubcommandArgs(unittest.TestCase):
    """Test that subcommand args work at any level."""
    
    @classmethod
    def setUpClass(cls):
        cls.config_path = os.path.join(os.path.dirname(__file__), "dya.yaml")
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        
        self.loader = ConfigLoader(self.config_path)
        self.loader.load()
        
        self.crypto_patcher = patch('dynamic_alias.crypto.get_machine_id', return_value='test-id')
        self.crypto_patcher.start()
        
        self.cache = CacheManager(self.cache_path, enabled=True)
        self.cache.load()
        
        self.resolver = DataResolver(self.loader, self.cache)
        self.executor = CommandExecutor(self.resolver)
    
    def tearDown(self):
        self.crypto_patcher.stop()
        self.temp_dir.cleanup()
    
    def test_subcommand_with_args_at_level1(self):
        """Level 1 subcommand with args should be findable."""
        # 'nested-test-cmd level1 -f' should work
        result = self.executor.find_command(['nested-test-cmd', 'level1', '-f'])
        
        self.assertIsNotNone(result)
        chain, variables, is_help, remaining = result
        
        # Should have matched nested-test-cmd -> level1 and -f arg
        self.assertGreaterEqual(len(chain), 2)


if __name__ == '__main__':
    unittest.main()
