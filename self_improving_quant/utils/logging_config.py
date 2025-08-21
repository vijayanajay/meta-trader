import logging
import sys

__all__ = ["setup_logging"]


def setup_logging(level: int = logging.INFO) -> None:
    """
    Sets up a centralized logger.

    Args:
        level: The minimum logging level to output.
    """
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a handler to print to stdout
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Add the handler to the root logger
    logger.addHandler(handler)
