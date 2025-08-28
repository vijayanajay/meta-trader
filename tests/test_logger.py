import pytest
import logging
from pathlib import Path

from praxis_engine.core.logger import get_logger

@pytest.fixture(autouse=True)
def cleanup_handlers():
    """Remove handlers from the root logger after each test."""
    yield
    root_logger = logging.getLogger("praxis_engine")
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

def test_logger_normal_mode(tmp_path: Path):
    """Tests logger in normal (non-debug) mode."""
    # Arrange
    logger = get_logger("praxis_engine.test_normal", debug=False)

    # Assert
    assert len(logger.handlers) == 2

    console_handler = logger.handlers[0]
    assert isinstance(console_handler, logging.StreamHandler)
    assert console_handler.level == logging.INFO
    assert "%(asctime)s - %(message)s" in console_handler.formatter._fmt

    file_handler = logger.handlers[1]
    assert isinstance(file_handler, logging.FileHandler)
    assert file_handler.level == logging.DEBUG
    assert "results.txt" in file_handler.baseFilename

def test_logger_debug_mode(tmp_path: Path):
    """Tests logger in debug mode."""
    # Arrange
    logger = get_logger("praxis_engine.test_debug", debug=True)

    # Assert
    assert len(logger.handlers) == 2

    console_handler = logger.handlers[0]
    assert isinstance(console_handler, logging.StreamHandler)
    assert console_handler.level == logging.DEBUG
    assert "%(asctime)s - %(name)s - %(levelname)s - %(message)s" in console_handler.formatter._fmt

def test_log_file_creation_and_content(tmp_path: Path):
    """Tests that the log file is created and written to."""
    # Arrange
    log_file = Path("results/results.txt")
    if log_file.exists():
        log_file.unlink()

    logger = get_logger("praxis_engine.test_file", debug=True)

    # Act
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")

    # Close handlers to ensure logs are flushed to disk
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    # Assert
    assert log_file.exists()
    content = log_file.read_text()
    assert "This is a debug message." in content
    assert "This is an info message." in content
