"""
Dynamic Dict Chaining Tests
Test Rules:
    @system_rules.txt
    @global-test-rules.md

Tests for:
- Dynamic dict chaining: dict -> dynamic_dict -> dynamic_dict -> command
- Variable substitution in dynamic dict commands
- Priority-based resolution order
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
from dynamic_alias.cache import CacheManager
from dynamic_alias.resolver import DataResolver
from dynamic_alias.executor import CommandExecutor


class TestDynamicDictChaining(unittest.TestCase):
    """Test dynamic dict chaining: dict -> dynamic_dict -> dynamic_dict."""
    
    @classmethod
    def setUpClass(cls):
        cls.config_file = os.path.join(os.path.dirname(__file__), "dya.yaml")
        assert os.path.exists(cls.config_file), f"Config file not found: {cls.config_file}"
        
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "dya.json")
        
        self.loader = ConfigLoader(self.config_file)
        self.loader.load()
        
        self.cache = CacheManager(self.cache_path, enabled=True)
        # Mock crypto to prevent ioreg calls interfering with subprocess mocks
        self.crypto_patcher = patch('dynamic_alias.crypto.get_machine_id', return_value='test-machine-id')
        self.crypto_patcher.start()
        self.cache.load()
        
        self.resolver = DataResolver(self.loader, self.cache)
        self.executor = CommandExecutor(self.resolver)

    def tearDown(self):
        self.crypto_patcher.stop()
        self.temp_dir.cleanup()

    # =========================================================================
    # Base Dict Resolution Tests
    # =========================================================================
    
    def test_base_dict_resolves(self):
        """Base dict (base_prefix) should resolve correctly."""
        data = self.resolver.resolve_one('base_prefix')
        self.assertIsNotNone(data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['prefix'], 'CHAIN')
    
    # =========================================================================
    # Level 1 Chaining Tests (dict -> dynamic_dict)
    # =========================================================================
    
    def test_level1_dynamic_dict_references_dict(self):
        """level1_chain should reference base_prefix dict value."""
        # level1_chain command uses $${base_prefix.prefix}
        # Output should include "CHAIN-LEVEL1"
        
        with patch('dynamic_alias.resolver.subprocess.run') as mock_run:
            # First call: level1_chain execution (base_prefix is already a static dict)
            mock_run.return_value.stdout = '[{"value": "CHAIN-LEVEL1"}]'
            mock_run.return_value.returncode = 0
            
            data = self.resolver.resolve_one('level1_chain')
            
            # Verify the command was called with substituted variable
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            
            # The command should have CHAIN substituted (from base_prefix.prefix)
            self.assertIn('CHAIN', cmd)
            
            # Result should have the expected value
            self.assertIsNotNone(data)
            self.assertEqual(data[0]['result'], 'CHAIN-LEVEL1')
    
    def test_level1_uses_dict_direct_mode(self):
        """level1_chain should use direct mode (position 0) for dict reference."""
        # Mock subprocess to capture the actual command being executed
        with patch('dynamic_alias.resolver.subprocess.run') as mock_run:
            mock_run.return_value.stdout = '[{"value": "CHAIN-LEVEL1"}]'
            mock_run.return_value.returncode = 0
            
            self.resolver.resolve_one('level1_chain')
            
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            
            # Should NOT contain placeholder - should be resolved
            self.assertNotIn('$${base_prefix.prefix}', cmd)
            self.assertIn('CHAIN', cmd)
    
    # =========================================================================
    # Level 2 Chaining Tests (dynamic_dict -> dynamic_dict)
    # =========================================================================
    
    def test_level2_dynamic_dict_references_level1(self):
        """level2_chain should reference level1_chain dynamic_dict value."""
        with patch('dynamic_alias.resolver.subprocess.run') as mock_run:
            # Setup mock responses for both dynamic dicts
            # level1_chain command has $${base_prefix.prefix} -> CHAIN
            # level2_chain command has $${level1_chain.result} -> should be resolved from level1
            call_count = [0]
            
            def subprocess_side_effect(cmd, **kwargs):
                call_count[0] += 1
                result = MagicMock()
                result.returncode = 0
                # First call is for level1_chain, second is for level2_chain
                if call_count[0] == 1:
                    result.stdout = '[{"value": "CHAIN-LEVEL1"}]'
                else:
                    result.stdout = '[{"value": "CHAIN-LEVEL1-LEVEL2"}]'
                return result
            
            mock_run.side_effect = subprocess_side_effect
            
            data = self.resolver.resolve_one('level2_chain')
            
            # Should have called subprocess twice (level1 first, then level2)
            self.assertEqual(mock_run.call_count, 2)
            
            # Result should have the chained value
            self.assertIsNotNone(data)
            self.assertEqual(data[0]['result'], 'CHAIN-LEVEL1-LEVEL2')
    
    def test_level2_substitutes_level1_result(self):
        """level2_chain command should have level1_chain.result substituted."""
        with patch('dynamic_alias.resolver.subprocess.run') as mock_run:
            def subprocess_side_effect(cmd, **kwargs):
                result = MagicMock()
                result.returncode = 0
                if 'base_prefix' in str(cmd) or 'CHAIN-LEVEL1' not in str(cmd):
                    # First call - level1_chain
                    result.stdout = '[{"value": "CHAIN-LEVEL1"}]'
                else:
                    # Second call - level2_chain (should have CHAIN-LEVEL1 in cmd)
                    result.stdout = '[{"value": "CHAIN-LEVEL1-LEVEL2"}]'
                return result
            
            mock_run.side_effect = subprocess_side_effect
            
            self.resolver.resolve_one('level2_chain')
            
            # Check the second call (level2_chain) has the substituted value
            second_call_cmd = mock_run.call_args_list[1][0][0]
            self.assertIn('CHAIN-LEVEL1', second_call_cmd)
            self.assertNotIn('$${level1_chain.result}', second_call_cmd)
    
    # =========================================================================
    # Full Chain Tests (dict -> dynamic_dict -> dynamic_dict -> command)
    # =========================================================================
    
    def test_chain_test_command_uses_level2_result(self):
        """chain-test command should resolve level2_chain.result."""
        with patch('dynamic_alias.resolver.subprocess.run') as mock_run:
            def subprocess_side_effect(cmd, **kwargs):
                result = MagicMock()
                result.returncode = 0
                if 'CHAIN-LEVEL1' not in str(cmd):
                    result.stdout = '[{"value": "CHAIN-LEVEL1"}]'
                else:
                    result.stdout = '[{"value": "CHAIN-LEVEL1-LEVEL2"}]'
                return result
            
            mock_run.side_effect = subprocess_side_effect
            
            # Find and test the command
            cmd_result = self.executor.find_command(['chain-test'])
            self.assertIsNotNone(cmd_result)
            
            chain, variables, is_help, remaining = cmd_result
            self.assertEqual(len(chain), 1)
            self.assertEqual(chain[0].alias, 'chain-test')
    
    # =========================================================================
    # Priority Order Tests
    # =========================================================================
    
    def test_dynamic_dicts_sorted_by_priority(self):
        """Dynamic dicts should be sorted by priority (lower values first)."""
        # base_prefix is a dict (no priority)
        # level1_chain has priority 1
        # level2_chain has priority 2
        
        dd_names = list(self.loader.dynamic_dicts.keys())
        
        # Find positions of our test dicts
        if 'level1_chain' in dd_names and 'level2_chain' in dd_names:
            level1_idx = dd_names.index('level1_chain')
            level2_idx = dd_names.index('level2_chain')
            # level1 should come before level2
            self.assertLess(
                self.loader.dynamic_dicts['level1_chain'].priority,
                self.loader.dynamic_dicts['level2_chain'].priority
            )
    
    def test_resolve_order_respects_dependencies(self):
        """When resolving level2, level1 should be resolved first."""
        with patch('dynamic_alias.resolver.subprocess.run') as mock_run:
            call_order = []
            
            def subprocess_side_effect(cmd, **kwargs):
                call_order.append(cmd)
                result = MagicMock()
                result.returncode = 0
                if 'CHAIN-LEVEL1' not in str(cmd):
                    result.stdout = '[{"value": "CHAIN-LEVEL1"}]'
                else:
                    result.stdout = '[{"value": "CHAIN-LEVEL1-LEVEL2"}]'
                return result
            
            mock_run.side_effect = subprocess_side_effect
            
            # Resolve level2 directly - should trigger level1 resolution first
            self.resolver.resolve_one('level2_chain')
            
            # First call should be for level1 (contains base_prefix reference)
            # Second call should be for level2 (contains level1 result)
            self.assertEqual(len(call_order), 2)
            self.assertIn('CHAIN', call_order[0])  # level1 has $${base_prefix.prefix} -> CHAIN
            self.assertIn('CHAIN-LEVEL1', call_order[1])  # level2 has resolved level1 value
    
    # =========================================================================
    # Caching Tests
    # =========================================================================
    
    def test_chained_results_are_cached(self):
        """Resolved chained dynamic dicts should be cached."""
        with patch('dynamic_alias.resolver.subprocess.run') as mock_run:
            mock_run.return_value.stdout = '[{"value": "CACHED-VALUE"}]'
            mock_run.return_value.returncode = 0
            
            # First resolution
            self.resolver.resolve_one('level1_chain')
            first_call_count = mock_run.call_count
            
            # Second resolution should use cache (no subprocess call)
            self.resolver.resolve_one('level1_chain')
            second_call_count = mock_run.call_count
            
            # Should not have made additional calls
            self.assertEqual(first_call_count, second_call_count)
            
            # Should be in resolved_data
            self.assertIn('level1_chain', self.resolver.resolved_data)


class TestChainingEdgeCases(unittest.TestCase):
    """Test edge cases in dynamic dict chaining."""
    
    @classmethod
    def setUpClass(cls):
        cls.config_file = os.path.join(os.path.dirname(__file__), "dya.yaml")
        
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "dya.json")
        
        self.loader = ConfigLoader(self.config_file)
        self.loader.load()
        
        self.cache = CacheManager(self.cache_path, enabled=True)
        # Mock crypto to prevent ioreg calls
        self.crypto_patcher = patch('dynamic_alias.crypto.get_machine_id', return_value='test-machine-id')
        self.crypto_patcher.start()
        self.cache.load()
        
        self.resolver = DataResolver(self.loader, self.cache)

    def tearDown(self):
        self.crypto_patcher.stop()
        self.temp_dir.cleanup()
    
    def test_unresolved_reference_keeps_placeholder(self):
        """If referenced source doesn't exist, placeholder should remain."""
        import re
        
        # Simulate a command with non-existent source
        template = 'echo $${nonexistent.key}'
        
        def replace_var(match):
            source = match.group(1)
            key = match.group(2)
            data_list = self.resolver.resolve_one(source)
            if data_list:
                return str(data_list[0].get(key, match.group(0)))
            return match.group(0)
        
        resolved = re.sub(r'\$\$\{(\w+)\.(\w+)\}', replace_var, template)
        
        # Placeholder should remain
        self.assertIn('$${nonexistent.key}', resolved)
    
    def test_missing_key_keeps_placeholder(self):
        """If key doesn't exist in source, placeholder should remain."""
        import re
        
        # base_prefix exists but doesn't have 'nonexistent_key'
        template = 'echo $${base_prefix.nonexistent_key}'
        
        def replace_var(match):
            source = match.group(1)
            key = match.group(2)
            data_list = self.resolver.resolve_one(source)
            if data_list:
                return str(data_list[0].get(key, match.group(0)))
            return match.group(0)
        
        resolved = re.sub(r'\$\$\{(\w+)\.(\w+)\}', replace_var, template)
        
        # Placeholder should remain (key doesn't exist)
        self.assertIn('$${base_prefix.nonexistent_key}', resolved)
    
    def test_static_dicts_always_available_for_dynamic_dicts(self):
        """Static dicts should always be resolvable by dynamic dicts."""
        # Static dicts don't have priority and should always be available
        data = self.resolver.resolve_one('base_prefix')
        self.assertIsNotNone(data)
        self.assertEqual(data[0]['prefix'], 'CHAIN')


if __name__ == '__main__':
    unittest.main()
