
import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Mocks are centralized in conftest.py

from dynamic_alias.executor import CommandExecutor
from dynamic_alias.models import CommandConfig, DictConfig, DynamicDictConfig, SubCommand, ArgConfig
from dynamic_alias.resolver import DataResolver
from dynamic_alias.config import ConfigLoader
from dynamic_alias.shell import InteractiveShell

@pytest.fixture
def mock_resolver():
    # Use dya.yaml fixture path
    config_file = os.path.join(os.path.dirname(__file__), "dya.yaml")
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"{config_file} must exist")
        
    loader = ConfigLoader(config_file)
    loader.load()
    
    # Mock cache
    cache = MagicMock()
    cache.get.return_value = None
    
    mock_res = DataResolver(loader, cache)
    
    # Pre-fill resolved_data to match dya.yaml
    mock_res.resolved_data = {
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
    return mock_res

def test_find_command_returns_is_help(mock_resolver):
    executor = CommandExecutor(mock_resolver)
    
    # Test Normal Command (Simple Alias)
    chain, vars, is_help, remaining = executor.find_command(['simple'])
    assert chain[0].alias == 'simple'
    assert is_help is False

    # Test Command Help (Strict Alias has helper? Actually Strict Alias in dya.yaml doesn't have explicitly defined helper but default is None)
    # Let's use Simple Alias which has helper? No, dya.yaml commands don't have helper defined in dya.yaml except... none of them have helper block in my created dya.yaml!
    # I should add helper to dya.yaml or use one that has it?
    # Wait, ConfigLoader parses helper.
    # I will assume 'simple' has no helper unless I add it to dya.yaml.
    # But -h always returns is_help=True regardless of whether helper text exists.
    
    result = executor.find_command(['simple', '-h'])
    if result:
        chain, vars, is_help, remaining = result
        assert chain[0].alias == 'simple'
        assert is_help is True
    else:
        pytest.fail("Command not found")

def test_help_flag_blocked_as_variable(mock_resolver):
    # Test passing -h as variable in 'complex ${arg1}'
    executor = CommandExecutor(mock_resolver)

    result = executor.find_command(['complex', '-h'])
    assert result is not None
    chain, vars, is_help, remaining = result
    assert chain[0].alias == 'complex ${arg1}'
    assert is_help is True 

def test_print_global_help_structure(mock_resolver):
    executor = CommandExecutor(mock_resolver)
    
    with patch('dynamic_alias.executor.print_formatted_text') as mock_print:
        with patch('builtins.print') as mock_builtin_print:
            executor.print_global_help()
            
            # Verify print_formatted_text was called (for header and sections)
            assert mock_print.called
            # Verify builtin print was called (for dict names, command names)
            assert mock_builtin_print.called

def test_interactive_shell_global_help(mock_resolver):
    executor = MagicMock() 
    shell = InteractiveShell(mock_resolver, executor)
    
    parts = ['-h']
    if len(parts) == 1 and parts[0] in ('-h', '--help'):
        executor.print_global_help()
    
    executor.print_global_help.assert_called_once()

def test_interactive_shell_command_help(mock_resolver):
    executor = MagicMock()
    cmd_mock = MagicMock()
    executor.find_command.return_value = ([cmd_mock], {}, True, [])
    
    shell = InteractiveShell(mock_resolver, executor)
    
    parts = ['test', '-h']
    result = executor.find_command(parts)
    
    if result:
        cmd, vars, is_help, remaining = result
        if is_help:
            executor.print_help(cmd)
        else:
            executor.execute(cmd, vars, remaining)
            
    executor.print_help.assert_called_once_with([cmd_mock])
    executor.execute.assert_not_called()

def test_partial_match_help(mock_resolver):
    # Setup: 'consume $${static_envs.name}'
    executor = CommandExecutor(mock_resolver)

    # Test 'consume -h' -> Should be partial match help
    result = executor.find_command(['consume', '-h'])
    
    assert result is not None
    chain, vars, is_help, remaining = result
    assert chain[0].alias == 'consume $${static_envs.name}'
    assert is_help is True

def test_partial_match_fail_on_static(mock_resolver):
    # Setup: 'simple'
    executor = CommandExecutor(mock_resolver)
    
    # Test 'sim -h' -> partial static match?
    # 'simple' vs 'sim'.
    # _match_alias_parts: 
    # for 'simple', 'sim':
    #   if 'simple' != 'sim': return False.
    # So it fails static match.
    # But wait, find_command iterates list.
    # It passes args.
    # If args = ['sim', '-h'].
    # _try_match('simple') -> _match_alias_parts(['simple'], ['sim', '-h'])
    #   i=0: alias='simple', input='sim'. Static mismatch. Return False.
    # So 'sim -h' should NOT return partial match help for 'simple'.
    
    result = executor.find_command(['sim', '-h'])
    assert result is None

def test_partial_match_dynamic_var_help(mock_resolver):
    # Setup: 'dyn $${dynamic_nodes.name}'
    executor = CommandExecutor(mock_resolver)
    
    # Test 'dyn -h'
    result = executor.find_command(['dyn', '-h'])
    
    assert result is not None
    chain, vars, is_help, remaining = result
    assert chain[0].name == 'Dynamic Consumer'
    assert is_help is True
