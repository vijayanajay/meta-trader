"""A simple, reusable retry decorator."""

import logging
import time
from functools import wraps
from typing import Any, Callable, ParamSpec, Type, TypeVar

__all__ = ["retry_on_failure"]

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def retry_on_failure(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    A decorator to retry a function call on failure with exponential backoff.

    Args:
        retries: The maximum number of retries.
        delay: The initial delay between retries in seconds.
        backoff: The factor by which to multiply the delay for each subsequent retry.
        exceptions: A tuple of exception types to catch and retry on.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            _retries, _delay = retries, delay
            while _retries > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    _retries -= 1
                    if _retries == 0:
                        logger.error(f"Function {func.__name__} failed after {retries} retries. Re-raising.")
                        raise

                    logger.warning(
                        f"Function {func.__name__} failed with {e.__class__.__name__}. "
                        f"Retrying in {_delay:.2f}s... ({_retries} retries left)"
                    )
                    time.sleep(_delay)
                    _delay *= backoff
            # This part should be unreachable if retries > 0, but mypy needs it
            raise RuntimeError("Exited retry loop unexpectedly.")

        return wrapper

    return decorator
