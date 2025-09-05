import subprocess
from praxis_engine.core.logger import get_logger

logger = get_logger(__name__)

# impure
import numpy as np
from typing import List

def generate_ascii_histogram(data: List[float], bins: int = 10) -> str:
    """
    Generates a simple ASCII histogram for a list of numbers.
    """
    if not data:
        return " (No data for histogram)"

    try:
        hist, bin_edges = np.histogram(data, bins=bins)
        max_freq = np.max(hist)
        bar_char = '█'
        max_bar_width = 30

        lines = []
        for i in range(len(hist)):
            freq = hist[i]
            bar_width = int((freq / max_freq) * max_bar_width) if max_freq > 0 else 0
            bar = bar_char * bar_width
            lines.append(f"{bin_edges[i]:>7.2f} - {bin_edges[i+1]:<7.2f} | {bar} ({freq})")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Could not generate ASCII histogram: {e}")
        return " (Error generating histogram)"


# impure
def get_git_commit_hash() -> str:
    """
    Retrieves the short git commit hash of the current HEAD.

    Returns:
        The short git commit hash as a string, or "N/A" if git is not
        installed, it's not a git repository, or any other error occurs.
    """
    try:
        # Execute the git command to get the short hash
        process = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8' # Explicitly set encoding
        )
        return process.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        # Handle cases where git is not installed or it's not a git repo
        logger.warning(f"Could not get git hash: {e}")
        return "N/A"
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred while getting git hash: {e}")
        return "N/A"


import functools
from typing import Any

def get_nested_attr(obj: Any, attr_string: str) -> Any:
    """
    Gets a nested attribute from an object based on a dot-separated string.
    """
    return functools.reduce(getattr, attr_string.split('.'), obj)


def set_nested_attr(obj: Any, attr_string: str, value: Any) -> None:
    """
    Sets a nested attribute on an object based on a dot-separated string.
    """
    attrs = attr_string.split('.')
    parent = functools.reduce(getattr, attrs[:-1], obj)
    setattr(parent, attrs[-1], value)
