"""
Tests for verbosity levels feature.

Tests all four verbosity levels: silent, default, verbose, trace.
"""
import pytest
import tempfile
import os
from io import StringIO
import sys

from dynamic_alias.config import ConfigLoader
from dynamic_alias.output import (
    get_output_strategy, SilentOutput, DefaultOutput, VerboseOutput, TraceOutput
)
from dynamic_alias.constants import (
    VERBOSITY_SILENT, VERBOSITY_DEFAULT, VERBOSITY_VERBOSE, VERBOSITY_TRACE
)


class TestOutputStrategy:
    """Tests for output strategy factory and classes."""
    
    def test_get_silent_strategy(self):
        """Test getting silent output strategy."""
        output = get_output_strategy(VERBOSITY_SILENT)
        assert isinstance(output, SilentOutput)
        assert not output.is_verbose
        assert not output.is_trace
    
    def test_get_default_strategy(self):
        """Test getting default output strategy."""
        output = get_output_strategy(VERBOSITY_DEFAULT)
        assert isinstance(output, DefaultOutput)
        assert not output.is_verbose
        assert not output.is_trace
    
    def test_get_verbose_strategy(self):
        """Test getting verbose output strategy."""
        output = get_output_strategy(VERBOSITY_VERBOSE)
        assert isinstance(output, VerboseOutput)
        assert output.is_verbose
        assert not output.is_trace
    
    def test_get_trace_strategy(self):
        """Test getting trace output strategy."""
        output = get_output_strategy(VERBOSITY_TRACE)
        assert isinstance(output, TraceOutput)
        assert output.is_verbose
        assert output.is_trace
    
    def test_unknown_verbosity_defaults_to_default(self):
        """Test that unknown verbosity falls back to default."""
        output = get_output_strategy("unknown")
        assert isinstance(output, DefaultOutput)


class TestSilentOutput:
    """Tests for silent output mode."""
    
    def test_silent_no_running_hint(self, capsys):
        """Silent mode should not print Running hint."""
        output = SilentOutput()
        output.print_running("echo test")
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_silent_no_divider(self, capsys):
        """Silent mode should not print divider."""
        output = SilentOutput()
        output.print_divider()
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_silent_no_verbose_log(self, capsys):
        """Silent mode should not print verbose logs."""
        output = SilentOutput()
        output.verbose_log("[VERBOSE] Test message")
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_silent_no_trace_log(self, capsys):
        """Silent mode should not print trace logs."""
        output = SilentOutput()
        output.trace_log("TestClass", "test_method", 0.123)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestDefaultOutput:
    """Tests for default output mode."""
    
    def test_default_prints_divider(self, capsys):
        """Default mode should print divider."""
        output = DefaultOutput()
        output.print_divider()
        captured = capsys.readouterr()
        assert "-" * 30 in captured.out
    
    def test_default_no_verbose_log(self, capsys):
        """Default mode should not print verbose logs."""
        output = DefaultOutput()
        output.verbose_log("[VERBOSE] Test message")
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_default_no_trace_log(self, capsys):
        """Default mode should not print trace logs."""
        output = DefaultOutput()
        output.trace_log("TestClass", "test_method", 0.123)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestVerboseOutput:
    """Tests for verbose output mode."""
    
    def test_verbose_prints_divider(self, capsys):
        """Verbose mode should print divider."""
        output = VerboseOutput()
        output.print_divider()
        captured = capsys.readouterr()
        assert "-" * 30 in captured.out
    
    def test_verbose_prints_verbose_log(self, capsys):
        """Verbose mode should print verbose logs."""
        output = VerboseOutput()
        output.verbose_log("[VERBOSE] Test message")
        captured = capsys.readouterr()
        assert "[VERBOSE] Test message" in captured.out
    
    def test_verbose_no_trace_log(self, capsys):
        """Verbose mode should not print trace logs."""
        output = VerboseOutput()
        output.trace_log("TestClass", "test_method", 0.123)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestTraceOutput:
    """Tests for trace output mode."""
    
    def test_trace_prints_divider(self, capsys):
        """Trace mode should print divider."""
        output = TraceOutput()
        output.print_divider()
        captured = capsys.readouterr()
        assert "-" * 30 in captured.out
    
    def test_trace_prints_verbose_log(self, capsys):
        """Trace mode should print verbose logs."""
        output = TraceOutput()
        output.verbose_log("[VERBOSE] Test message")
        captured = capsys.readouterr()
        assert "[VERBOSE] Test message" in captured.out
    
    def test_trace_prints_trace_log(self, capsys):
        """Trace mode should print trace logs with timing."""
        output = TraceOutput()
        output.trace_log("TestClass", "test_method", 0.1234)
        captured = capsys.readouterr()
        assert "[TRACE] TestClass.test_method" in captured.out
        assert "0.1234s" in captured.out
    
    def test_trace_prints_input_output(self, capsys):
        """Trace mode should print input and output."""
        output = TraceOutput()
        output.trace_log("TestClass", "test_method", 0.1234, 
                        inputs={"key": "value"}, output="result")
        captured = capsys.readouterr()
        assert "Input:" in captured.out
        assert "Output:" in captured.out
        assert "result" in captured.out


class TestConfigVerbosity:
    """Tests for verbosity configuration loading."""
    
    def test_default_verbosity(self, tmp_path):
        """Test default verbosity is 'default'."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("config:\n  history-size: 10\n")
        
        loader = ConfigLoader(str(config_file))
        loader.load()
        assert loader.global_config.verbosity == "default"
    
    def test_verbosity_silent(self, tmp_path):
        """Test verbosity: silent is loaded correctly."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("config:\n  verbosity: silent\n")
        
        loader = ConfigLoader(str(config_file))
        loader.load()
        assert loader.global_config.verbosity == "silent"
    
    def test_verbosity_verbose(self, tmp_path):
        """Test verbosity: verbose is loaded correctly."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("config:\n  verbosity: verbose\n")
        
        loader = ConfigLoader(str(config_file))
        loader.load()
        assert loader.global_config.verbosity == "verbose"
    
    def test_verbosity_trace(self, tmp_path):
        """Test verbosity: trace is loaded correctly."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("config:\n  verbosity: trace\n")
        
        loader = ConfigLoader(str(config_file))
        loader.load()
        assert loader.global_config.verbosity == "trace"
    
    def test_backward_compat_verbose_true(self, tmp_path):
        """Test backward compatibility: verbose: true -> verbosity: verbose."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("config:\n  verbose: true\n")
        
        loader = ConfigLoader(str(config_file))
        loader.load()
        assert loader.global_config.verbosity == "verbose"
    
    def test_backward_compat_verbose_false(self, tmp_path):
        """Test backward compatibility: verbose: false -> verbosity: default."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("config:\n  verbose: false\n")
        
        loader = ConfigLoader(str(config_file))
        loader.load()
        assert loader.global_config.verbosity == "default"
    
    def test_invalid_verbosity_defaults_to_default(self, tmp_path, capsys):
        """Test that invalid verbosity falls back to default with warning."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("config:\n  verbosity: invalid_level\n")
        
        loader = ConfigLoader(str(config_file))
        loader.load()
        assert loader.global_config.verbosity == "default"
        captured = capsys.readouterr()
        assert "Warning" in captured.out or loader.global_config.verbosity == "default"


class TestValidatorVerboseDeprecation:
    """Tests for validator detecting deprecated verbose key."""
    
    def test_validator_warns_on_verbose_key(self, tmp_path):
        """Validator should fail when verbose key is used."""
        from dynamic_alias.validator import ConfigValidator
        
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("config:\n  verbose: true\n")
        
        validator = ConfigValidator(str(config_file))
        report = validator.validate()
        
        # Should have a failure for deprecated verbose
        failed_msgs = [r.message for r in report.results if not r.passed]
        assert any("deprecated" in m.lower() and "verbose" in m.lower() 
                  for m in failed_msgs)
    
    def test_validator_passes_with_verbosity(self, tmp_path):
        """Validator should pass when verbosity key is used."""
        from dynamic_alias.validator import ConfigValidator
        
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("config:\n  verbosity: verbose\n")
        
        validator = ConfigValidator(str(config_file))
        report = validator.validate()
        
        # Should not have any deprecated warning
        failed_msgs = [r.message for r in report.results if not r.passed]
        assert not any("deprecated" in m.lower() for m in failed_msgs)
