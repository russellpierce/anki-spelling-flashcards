"""Spelling Words - Anki Deck Generator for Spelling Test Preparation."""

import sys
from pathlib import Path

from loguru import logger

__version__ = "0.1.0"


def configure_logging(log_file: str | None = None, level: str = "INFO") -> None:
    """Configure loguru logger with specified level and optional log file.

    Args:
        log_file: Optional path to log file. If None, logs only to stderr.
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to INFO.

    Example:
        >>> configure_logging(level="DEBUG")
        >>> configure_logging(log_file="app.log", level="INFO")
    """
    # Remove default handler
    logger.remove()

    # Add stderr handler with formatted output
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True,
    )

    # Add file handler if specified
    if log_file:
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=level,
            rotation="10 MB",
            retention="1 week",
        )


def install_exception_hook() -> None:
    """Install custom exception hook to log uncaught exceptions.

    This ensures that any uncaught exception is logged with full traceback
    before the program exits.
    """

    def exception_handler(exc_type, exc_value, exc_traceback):
        """Custom exception handler that logs exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupts
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.opt(exception=(exc_type, exc_value, exc_traceback)).critical("Uncaught exception")

    sys.excepthook = exception_handler


# Export public API
__all__ = ["__version__", "configure_logging", "install_exception_hook"]
