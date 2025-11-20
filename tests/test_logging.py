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

import sys

from loguru import logger
from spelling_words import configure_logging, install_exception_hook


def test_logger_can_be_imported():
    """Test that we can import the logger from spelling_words."""
    assert configure_logging is not None


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
