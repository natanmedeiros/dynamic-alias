"""
Pytest configuration - runs before all tests
Centralizes prompt_toolkit mocking to avoid interference
"""
import sys
from unittest.mock import MagicMock

# Mock prompt_toolkit BEFORE any test files import dynamic_alias modules
sys.modules['prompt_toolkit'] = MagicMock()
sys.modules['prompt_toolkit.shortcuts'] = MagicMock()
sys.modules['prompt_toolkit.formatted_text'] = MagicMock()
sys.modules['prompt_toolkit.key_binding'] = MagicMock()
sys.modules['prompt_toolkit.history'] = MagicMock()
sys.modules['prompt_toolkit.patch_stdout'] = MagicMock()
sys.modules['prompt_toolkit.completion'] = MagicMock()
sys.modules['prompt_toolkit.styles'] = MagicMock()

# Mock History class for shell.py inheritance
class MockHistory:
    def load_history_strings(self):
        return []
    def store_string(self, string):
        pass
sys.modules['prompt_toolkit.history'].History = MockHistory

# Mock Completer for completer.py inheritance
class MockCompleter:
    def get_completions(self, document, complete_event):
        pass
sys.modules['prompt_toolkit.completion'].Completer = MockCompleter

# Mock Completion class
class MockCompletion:
    def __init__(self, text, start_position=0, display=None):
        self.text = text
        self.start_position = start_position
        self.display = display
sys.modules['prompt_toolkit.completion'].Completion = MockCompletion
