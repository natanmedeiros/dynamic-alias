"""
Output Strategy Module

Implements Strategy pattern for output handling based on verbosity level.

Verbosity Levels:
    - silent: No Running hint, no dividers
    - default: Running hint + dividers, no verbose logs
    - verbose: All of default + verbose logs
    - trace: All of verbose + method timing with input/output
"""
from abc import ABC, abstractmethod
from functools import wraps
import time
import json
from typing import Any, Callable

from .constants import (
    VERBOSITY_SILENT, VERBOSITY_DEFAULT, VERBOSITY_VERBOSE, VERBOSITY_TRACE
)


class OutputStrategy(ABC):
    """Abstract base class for output strategies."""
    
    @abstractmethod
    def print_running(self, cmd: str) -> None:
        """Print the 'Running: <command>' message."""
        pass
    
    @abstractmethod
    def print_divider(self) -> None:
        """Print a divider line."""
        pass
    
    @abstractmethod
    def verbose_log(self, msg: str) -> None:
        """Print a verbose log message."""
        pass
    
    @abstractmethod
    def trace_log(self, class_name: str, method: str, elapsed: float, 
                  inputs: Any = None, output: Any = None) -> None:
        """Print a trace log with timing and optionally input/output."""
        pass
    
    @property
    @abstractmethod
    def is_verbose(self) -> bool:
        """Check if verbose logging is enabled."""
        pass
    
    @property
    @abstractmethod
    def is_trace(self) -> bool:
        """Check if trace logging is enabled."""
        pass


class SilentOutput(OutputStrategy):
    """Silent mode: No output except errors."""
    
    def print_running(self, cmd: str) -> None:
        pass  # No output
    
    def print_divider(self) -> None:
        pass  # No divider
    
    def verbose_log(self, msg: str) -> None:
        pass
    
    def trace_log(self, class_name: str, method: str, elapsed: float,
                  inputs: Any = None, output: Any = None) -> None:
        pass
    
    @property
    def is_verbose(self) -> bool:
        return False
    
    @property
    def is_trace(self) -> bool:
        return False


class DefaultOutput(OutputStrategy):
    """Default mode: Running hint + dividers, no verbose logs."""
    
    def print_running(self, cmd: str) -> None:
        from prompt_toolkit.shortcuts import print_formatted_text
        from prompt_toolkit.formatted_text import HTML
        print_formatted_text(HTML(f"<b><green>Running:</green></b> {cmd}"))
    
    def print_divider(self) -> None:
        print("-" * 30)
    
    def verbose_log(self, msg: str) -> None:
        pass  # No verbose logs in default mode
    
    def trace_log(self, class_name: str, method: str, elapsed: float,
                  inputs: Any = None, output: Any = None) -> None:
        pass  # No trace logs in default mode
    
    @property
    def is_verbose(self) -> bool:
        return False
    
    @property
    def is_trace(self) -> bool:
        return False


class VerboseOutput(DefaultOutput):
    """Verbose mode: All of default + verbose logs."""
    
    def verbose_log(self, msg: str) -> None:
        print(msg)
    
    @property
    def is_verbose(self) -> bool:
        return True


class TraceOutput(VerboseOutput):
    """Trace mode: All of verbose + method timing with input/output."""
    
    def trace_log(self, class_name: str, method: str, elapsed: float,
                  inputs: Any = None, output: Any = None) -> None:
        parts = [f"[TRACE] {class_name}.{method} ({elapsed:.4f}s)"]
        
        if inputs is not None:
            try:
                inputs_str = self._format_value(inputs)
                parts.append(f"  Input: {inputs_str}")
            except Exception:
                parts.append(f"  Input: <unable to serialize>")
        
        if output is not None:
            try:
                output_str = self._format_value(output)
                parts.append(f"  Output: {output_str}")
            except Exception:
                parts.append(f"  Output: <unable to serialize>")
        
        print("\n".join(parts))
    
    def _format_value(self, value: Any) -> str:
        """Format a value for trace output, truncating if too long."""
        if value is None:
            return "None"
        if isinstance(value, (str, int, float, bool)):
            s = repr(value)
        elif isinstance(value, (list, dict)):
            s = json.dumps(value, ensure_ascii=False, default=str)
        else:
            s = repr(value)
        
        # Truncate if too long
        max_len = 200
        if len(s) > max_len:
            s = s[:max_len] + "..."
        return s
    
    @property
    def is_trace(self) -> bool:
        return True


# Strategy factory
_strategies = {
    VERBOSITY_SILENT: SilentOutput,
    VERBOSITY_DEFAULT: DefaultOutput,
    VERBOSITY_VERBOSE: VerboseOutput,
    VERBOSITY_TRACE: TraceOutput,
}

# Cache for strategy instances
_strategy_cache = {}


def get_output_strategy(verbosity: str) -> OutputStrategy:
    """
    Get the output strategy for the given verbosity level.
    
    Args:
        verbosity: One of 'silent', 'default', 'verbose', 'trace'
    
    Returns:
        OutputStrategy instance
    """
    if verbosity not in _strategy_cache:
        strategy_class = _strategies.get(verbosity, DefaultOutput)
        _strategy_cache[verbosity] = strategy_class()
    return _strategy_cache[verbosity]


def trace_method(output: OutputStrategy):
    """
    Decorator for automatic method tracing.
    
    Only logs if output.is_trace is True.
    
    Usage:
        @trace_method(output)
        def my_method(self, arg1, arg2):
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not output.is_trace:
                return func(*args, **kwargs)
            
            start = time.time()
            # Capture inputs (skip 'self' if present)
            inputs = args[1:] if args and hasattr(args[0], '__class__') else args
            if kwargs:
                inputs = (inputs, kwargs)
            
            result = func(*args, **kwargs)
            
            elapsed = time.time() - start
            class_name = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else ""
            
            output.trace_log(class_name, func.__name__, elapsed, inputs, result)
            
            return result
        return wrapper
    return decorator
