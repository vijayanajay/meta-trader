import logging
import sys
from pathlib import Path

# Define a custom log level for summary reporting
SUMMARY_LEVEL_NUM = 25  # Between INFO and WARNING
SUMMARY_LEVEL_NAME = "SUMMARY"
logging.addLevelName(SUMMARY_LEVEL_NUM, SUMMARY_LEVEL_NAME)

def summary(self, message, *args, **kws):
    if self.isEnabledFor(SUMMARY_LEVEL_NUM):
        self._log(SUMMARY_LEVEL_NUM, message, args, **kws)

logging.Logger.summary = summary


def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger with two handlers:
    1. A file handler that logs detailed INFO messages to `backtest_results.log`.
    2. A stream handler that logs only SUMMARY level messages to the console.
    """
    logger = logging.getLogger(name)

    # Prevent adding handlers multiple times
    if not logger.handlers:
        logger.setLevel(logging.INFO)  # Set the lowest level to capture all messages

        # Create results directory if it doesn't exist
        Path("results").mkdir(exist_ok=True)

        # 1. File Handler for detailed logs
        # Overwrites the file for each new run
        file_handler = logging.FileHandler("results/backtest_results.log", mode='w')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # 2. Stream Handler for summary console output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(SUMMARY_LEVEL_NUM) # Only log summary messages
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger
