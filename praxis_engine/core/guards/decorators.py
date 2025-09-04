"""
Guard helpers: argument normalizer for validate methods.

Provides a decorator to allow guards to accept either (df, signal) or
(df, current_index, signal) while implementing a single normalized interface.
"""
from __future__ import annotations

from typing import Callable, Any, TypeVar
import functools
import pandas as pd

from praxis_engine.core.models import Signal

F = TypeVar('F', bound=Callable[..., Any])

def normalize_guard_args(func: F) -> F:
    """Decorator that normalizes validate args to (full_df, current_index, signal).

    If caller passed (full_df, signal), current_index will default to len(full_df)-1.
    """

    @functools.wraps(func)
    def wrapper(self: Any, full_df: pd.DataFrame, *args: Any, **kwargs: Any) -> Any:
        signal: Signal
        current_index: int

        if len(args) == 1:
            signal = args[0]
            current_index = len(full_df) - 1
        elif len(args) == 2:
            current_index, signal = args
        else:
            raise TypeError("validate() expects (full_df, signal) or (full_df, current_index, signal)")

        if not isinstance(current_index, int):
            raise TypeError("current_index must be an int")

        return func(self, full_df, current_index, signal)

    return wrapper  # type: ignore
