import subprocess
from praxis_engine.core.logger import get_logger

logger = get_logger(__name__)

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
