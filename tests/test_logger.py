import logging
import os
from pathlib import Path
from unittest.mock import patch

from praxis_engine.core.logger import get_logger, SUMMARY_LEVEL_NUM


def test_logger_setup():
    """
    Tests that the logger is set up correctly with two handlers.
    """
    # Clear any existing handlers
    logger = logging.getLogger("test_logger_setup")
    logger.handlers = []

    # Get the logger
    logger = get_logger("test_logger_setup")

    assert len(logger.handlers) == 2
    assert isinstance(logger.handlers[0], logging.FileHandler)
    assert isinstance(logger.handlers[1], logging.StreamHandler)


def test_log_file_creation_and_content(tmp_path: Path):
    """
    Tests that the log file is created and that messages are written to it.
    """
    # Change to a temporary directory to isolate log file creation
    os.chdir(tmp_path)

    # Clear any existing handlers
    logger = logging.getLogger("test_log_file")
    logger.handlers = []

    # Get the logger
    logger = get_logger("test_log_file")

    # Log some messages
    logger.info("This is an info message.")
    logger.debug("This is a debug message.")  # This should not be logged
    logger.summary("This is a summary message.") # This should be logged as INFO level

    log_file = Path("results/backtest_results.log")
    assert log_file.exists()

    log_content = log_file.read_text()
    assert "This is an info message." in log_content
    assert "This is a debug message." not in log_content
    assert "This is a summary message." in log_content


def test_console_output(capsys):
    """
    Tests that only SUMMARY level messages are printed to the console.
    """
    # Clear any existing handlers
    logger = logging.getLogger("test_console_output")
    logger.handlers = []
    logger.propagate = False

    # Get the logger and override console level for test purposes
    logger = get_logger("test_console_output")
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(SUMMARY_LEVEL_NUM)

    # Log some messages
    logger.info("This should not be on the console.")
    logger.warning("This is a warning, should not be on console.")
    logger.summary("This should be on the console.")

    captured = capsys.readouterr()
    assert "This should not be on the console." not in captured.err
    assert "This is a warning" not in captured.err
    assert "This should be on the console." in captured.out
