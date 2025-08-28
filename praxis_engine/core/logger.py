import logging
import sys
from pathlib import Path

# Ensure the results directory exists
Path("results").mkdir(exist_ok=True)

def get_logger(name: str, debug: bool = False) -> logging.Logger:
    """
    Configures and returns a logger with console and file handlers.

    Args:
        name: The name of the logger.
        debug: If True, sets the console logger to DEBUG level.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # Set logger to the lowest level to capture all messages

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_level = logging.DEBUG if debug else logging.INFO
    console_handler.setLevel(console_level)

    # Use a simpler format for INFO-level status tracking, and a detailed one for DEBUG
    if debug:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        console_formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # --- File Handler ---
    # This handler always logs DEBUG level messages to a file.
    file_handler = logging.FileHandler("results/results.txt", mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger
