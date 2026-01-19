import unittest
from unittest.mock import MagicMock, patch
from dynamic_alias.executor import CommandExecutor
from dynamic_alias.models import CommandConfig
from dynamic_alias.resolver import DataResolver

class TestStrictCommand(unittest.TestCase):
    def setUp(self):
        self.mock_resolver = MagicMock(spec=DataResolver)
        self.mock_resolver.resolved_data = {}
        # Mock config with commands
        self.mock_resolver.config = MagicMock()
        self.executor = CommandExecutor(self.mock_resolver)

    @patch('dynamic_alias.executor.print_formatted_text')
    @patch('dynamic_alias.executor._run_interactive_subprocess')
    def test_strict_true_execution(self, mock_run, mock_print):
        # Strict mode = True
        cmd = CommandConfig(
            name="StrictCmd",
            alias="strict",
            command="echo strict",
            strict=True
        )
        self.mock_resolver.config.commands = [cmd]
        
        # 1. Exact match -> Should run
        chain, vars, is_help, remaining = self.executor.find_command(["strict"])
        self.assertIsNotNone(chain)
        self.assertEqual(remaining, [])
        self.executor.execute(chain, vars, remaining)
        mock_run.assert_called()
        args, kwargs = mock_run.call_args
        self.assertIn("echo strict", args[0])

        mock_run.reset_mock()

        # 2. Extra args -> Should fail (print error and return, no subprocess)
        chain, vars, is_help, remaining = self.executor.find_command(["strict", "extra"])
        self.assertEqual(remaining, ["extra"])
        self.executor.execute(chain, vars, remaining)
        mock_run.assert_not_called()
        # Verify error message was printed
        # mock_print.assert_called_with(...) # Optional

    @patch('dynamic_alias.executor.print_formatted_text')
    @patch('dynamic_alias.executor._run_interactive_subprocess')
    def test_strict_false_execution(self, mock_run, mock_print):
        # Strict mode = False (default)
        cmd = CommandConfig(
            name="LooseCmd",
            alias="loose",
            command="echo loose",
            strict=False
        )
        self.mock_resolver.config.commands = [cmd]
        
        # 1. Extra args -> Should append
        chain, vars, is_help, remaining = self.executor.find_command(["loose", "extra", "args"])
        self.assertEqual(remaining, ["extra", "args"])
        self.executor.execute(chain, vars, remaining)
        mock_run.assert_called()
        args, kwargs = mock_run.call_args
        # Should be "echo loose 'extra' 'args'" (quoted)
        self.assertTrue("extra" in args[0])
        self.assertTrue("loose" in args[0])

if __name__ == '__main__':
    unittest.main()

