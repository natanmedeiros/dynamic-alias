"""
Signal Handling Tests

Tests for proper Ctrl+C/Ctrl+D handling when running interactive subprocesses.
Validates that:
- Terminal state is properly restored after subprocess exits
- Parent process survives subprocess termination
- Windows-specific signal handling works correctly
"""
import os
import sys
import unittest
import subprocess
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

from dynamic_alias.executor import (
    _save_terminal_state,
    _restore_terminal_state,
    _run_interactive_subprocess
)


class TestTerminalStateManagement(unittest.TestCase):
    """Test terminal state save/restore functions."""
    
    def test_save_terminal_state_returns_none_on_windows(self):
        """On Windows, _save_terminal_state should return None."""
        with patch('sys.platform', 'win32'):
            # Re-import would be needed for actual test, but logic is checked
            if sys.platform == 'win32':
                result = _save_terminal_state()
                self.assertIsNone(result)
    
    def test_restore_terminal_state_handles_none(self):
        """_restore_terminal_state should handle None gracefully."""
        # Should not raise any exception
        _restore_terminal_state(None)
    
    @unittest.skipIf(sys.platform == 'win32', "Unix-only test")
    def test_save_and_restore_terminal_state_unix(self):
        """On Unix, should save and restore terminal state."""
        state = _save_terminal_state()
        # State may be None if stdin is not a TTY (e.g., in CI)
        # Just ensure no exception is raised
        _restore_terminal_state(state)


class TestInteractiveSubprocessExecution(unittest.TestCase):
    """Test _run_interactive_subprocess function."""
    
    def test_simple_command_execution(self):
        """Simple command should execute and return exit code."""
        if sys.platform == 'win32':
            cmd = 'cmd /c echo hello'
        else:
            cmd = 'echo hello'
        
        return_code = _run_interactive_subprocess(cmd)
        self.assertEqual(return_code, 0)
    
    def test_command_with_non_zero_exit(self):
        """Command with non-zero exit should return that code."""
        if sys.platform == 'win32':
            cmd = 'cmd /c exit 42'
        else:
            cmd = 'exit 42'
        
        return_code = _run_interactive_subprocess(cmd)
        self.assertEqual(return_code, 42)
    
    def test_timeout_raises_exception(self):
        """Command that exceeds timeout should raise TimeoutExpired."""
        if sys.platform == 'win32':
            # Windows: use ping with wait
            cmd = 'ping -n 10 127.0.0.1 > nul'
        else:
            cmd = 'sleep 10'
        
        with self.assertRaises(subprocess.TimeoutExpired):
            _run_interactive_subprocess(cmd, timeout=0.5)
    
    @unittest.skipIf(sys.platform == 'win32', "Unix-only test")
    def test_terminal_reset_after_command(self):
        """Terminal should be reset after command execution on Unix."""
        # Run a command that might mess with terminal
        with patch('os.system') as mock_system:
            _run_interactive_subprocess('echo test')
            # Should have called stty sane
            mock_system.assert_called_with('stty sane 2>/dev/null')
    
    @unittest.skipIf(sys.platform != 'win32', "Windows-only test")
    def test_windows_uses_new_process_group(self):
        """On Windows, should use CREATE_NEW_PROCESS_GROUP flag."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            _run_interactive_subprocess('echo test')
            
            # Verify CREATE_NEW_PROCESS_GROUP was used
            call_kwargs = mock_popen.call_args[1]
            self.assertIn('creationflags', call_kwargs)
            self.assertEqual(
                call_kwargs['creationflags'],
                subprocess.CREATE_NEW_PROCESS_GROUP
            )


class TestSignalHandling(unittest.TestCase):
    """Test signal handling during subprocess execution."""
    
    @unittest.skipIf(sys.platform == 'win32', "Unix-only test")
    def test_sigint_ignored_in_parent_during_subprocess(self):
        """SIGINT should be ignored in parent during subprocess execution."""
        import signal
        
        # Create a script that sends SIGINT to parent
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\n')
            f.write(f'kill -INT {os.getpid()}\n')
            f.write('exit 0\n')
            f.flush()
            os.chmod(f.name, 0o755)
            
            try:
                # This should not raise KeyboardInterrupt
                return_code = _run_interactive_subprocess(f'bash {f.name}')
                # Process should complete normally
                self.assertEqual(return_code, 0)
            finally:
                os.unlink(f.name)
    
    @unittest.skipIf(sys.platform == 'win32', "Unix-only test")
    def test_sigint_handler_restored_after_subprocess(self):
        """Original SIGINT handler should be restored after subprocess."""
        import signal
        
        # Get current handler
        original_handler = signal.getsignal(signal.SIGINT)
        
        # Run a simple command
        _run_interactive_subprocess('echo test')
        
        # Verify handler is restored
        current_handler = signal.getsignal(signal.SIGINT)
        self.assertEqual(original_handler, current_handler)


class TestSubprocessTerminalCorruption(unittest.TestCase):
    """Test that subprocess doesn't leave terminal corrupted."""
    
    @unittest.skipIf(sys.platform == 'win32', "Unix-only test")
    def test_stty_sane_called_after_subprocess(self):
        """stty sane should be called after subprocess exits."""
        with patch('os.system') as mock_system:
            _run_interactive_subprocess('echo hello')
            
            # Find call to stty sane
            calls = [str(c) for c in mock_system.call_args_list]
            stty_calls = [c for c in calls if 'stty sane' in c]
            self.assertTrue(len(stty_calls) > 0, "stty sane should be called")
    
    @unittest.skipIf(sys.platform == 'win32', "Unix-only test")
    def test_stty_sane_called_even_on_timeout(self):
        """stty sane should be called even if command times out."""
        with patch('os.system') as mock_system:
            try:
                _run_interactive_subprocess('sleep 10', timeout=0.1)
            except subprocess.TimeoutExpired:
                pass
            
            # Find call to stty sane
            calls = [str(c) for c in mock_system.call_args_list]
            stty_calls = [c for c in calls if 'stty sane' in c]
            self.assertTrue(len(stty_calls) > 0, "stty sane should be called on timeout")


if __name__ == '__main__':
    unittest.main()
