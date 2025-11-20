"""Tests for logging configuration.

CRITICAL DIRECTIVE: TEST INTEGRITY
===================================
NEVER remove, disable, or work around a failing test without explicit user review and approval.

When a test fails:
1. STOP - Do not proceed with implementation
2. ANALYZE - Understand why the test is failing
3. DISCUSS - Present the failure to the user with exact error, root cause, and proposed solutions
4. WAIT - Get explicit user approval before modifying/removing/skipping the test

Tests are the specification. A failing test means either:
- The implementation is wrong (most common - fix the code)
- The test expectations are wrong (requires user discussion)
- The requirements have changed (requires user approval)
"""

import re
import sys

from loguru import logger
from spelling_words import configure_logging, install_exception_hook


def test_logger_can_be_imported():
    """Test that we can import the logger from spelling_words."""
    # This will fail until we implement the module
    assert configure_logging is not None


def test_configure_logging_with_default_level(tmp_path):
    """Test that configure_logging sets up logger with INFO level by default."""
    log_file = tmp_path / "test.log"

    # Remove existing handlers and configure
    logger.remove()
    configure_logging(log_file=str(log_file), level="INFO")

    # Log at different levels
    logger.debug("This should NOT appear")
    logger.info("This SHOULD appear")
    logger.warning("This SHOULD appear")

    # Read log file
    log_content = log_file.read_text()

    # Verify INFO and WARNING appear, but not DEBUG
    assert "This SHOULD appear" in log_content
    assert "This should NOT appear" not in log_content


def test_configure_logging_with_debug_level(tmp_path):
    """Test that configure_logging can be set to DEBUG level."""
    log_file = tmp_path / "test.log"

    # Remove existing handlers and configure
    logger.remove()
    configure_logging(log_file=str(log_file), level="DEBUG")

    # Log at different levels
    logger.debug("Debug message")
    logger.info("Info message")

    # Read log file
    log_content = log_file.read_text()

    # Verify DEBUG messages appear
    assert "Debug message" in log_content
    assert "Info message" in log_content


def test_log_format_includes_timestamp(tmp_path):
    """Test that log format includes timestamp."""
    log_file = tmp_path / "test.log"

    logger.remove()
    configure_logging(log_file=str(log_file), level="INFO")

    logger.info("Test message")

    log_content = log_file.read_text()

    # Check for timestamp pattern (YYYY-MM-DD HH:MM:SS)
    # Loguru default format includes this
    timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
    assert re.search(timestamp_pattern, log_content), "Log should contain timestamp"


def test_log_format_includes_level(tmp_path):
    """Test that log format includes log level."""
    log_file = tmp_path / "test.log"

    logger.remove()
    configure_logging(log_file=str(log_file), level="INFO")

    logger.info("Test message")
    logger.warning("Warning message")
    logger.error("Error message")

    log_content = log_file.read_text()

    # Verify log levels appear in output
    assert "INFO" in log_content
    assert "WARNING" in log_content
    assert "ERROR" in log_content


def test_exception_hook_logs_uncaught_exceptions(tmp_path, capsys):
    """Test that uncaught exceptions are logged."""
    log_file = tmp_path / "test.log"

    logger.remove()
    configure_logging(log_file=str(log_file), level="INFO")
    install_exception_hook()

    # Simulate uncaught exception by calling the hook directly
    try:
        msg = "Test exception"
        raise ValueError(msg)
    except ValueError:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        # Call the custom exception hook
        sys.excepthook(exc_type, exc_value, exc_traceback)

    # Read log file
    log_content = log_file.read_text()

    # Verify exception was logged
    assert "ValueError" in log_content
    assert "Test exception" in log_content
    assert "Traceback" in log_content or "traceback" in log_content


def test_logger_outputs_to_stderr_by_default(capsys):
    """Test that logger outputs to stderr in addition to file."""
    logger.remove()
    configure_logging(level="INFO")  # No log file, should use stderr

    logger.info("Test stderr message")

    captured = capsys.readouterr()

    # Loguru outputs to stderr by default
    assert "Test stderr message" in captured.err


def test_configure_logging_can_be_called_multiple_times(tmp_path):
    """Test that configure_logging can be called multiple times without error."""
    log_file = tmp_path / "test.log"

    # Should not raise an error when called multiple times
    logger.remove()
    configure_logging(log_file=str(log_file), level="INFO")
    configure_logging(log_file=str(log_file), level="DEBUG")

    logger.debug("Test message")
    log_content = log_file.read_text()

    # Should use the latest configuration (DEBUG level)
    assert "Test message" in log_content
