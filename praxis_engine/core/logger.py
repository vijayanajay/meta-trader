import logging
import sys
from pathlib import Path

def setup_file_logger(log_dir: str = "results", file_name: str = "backtest_results.log") -> None:
    """
    Configures the root logger with handlers for file and console output.
    This should be called once when the application starts.
    """
    root_logger = logging.getLogger()
    # Set the lowest level on the root logger to capture all messages
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers to prevent duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # File Handler for detailed logs
    results_dir = Path(log_dir)
    results_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(results_dir / file_name, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console Handler for progress and summaries
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger instance for the given name.
    The logger is configured by the setup_file_logger function.
    """
    return logging.getLogger(name)
