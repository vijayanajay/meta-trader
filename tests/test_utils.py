import subprocess
from unittest.mock import patch, MagicMock

from praxis_engine.utils import get_git_commit_hash

def test_get_git_commit_hash_success():
    """
    Tests that get_git_commit_hash returns the correct hash on success.
    """
    # Mock the subprocess.run call to simulate a successful git command
    mock_process = MagicMock()
    mock_process.stdout = "abcdef1\n"
    mock_process.check_returncode.return_value = None  # Not needed as check=True handles it

    with patch('subprocess.run', return_value=mock_process) as mock_run:
        commit_hash = get_git_commit_hash()

        # Assert that the function returns the stripped hash
        assert commit_hash == "abcdef1"

        # Assert that subprocess.run was called with the correct arguments
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )

def test_get_git_commit_hash_git_not_found():
    """
    Tests that get_git_commit_hash returns 'N/A' when git is not installed.
    """
    # Mock subprocess.run to raise FileNotFoundError
    with patch('subprocess.run', side_effect=FileNotFoundError("git not found")) as mock_run:
        commit_hash = get_git_commit_hash()

        # Assert that the function returns "N/A"
        assert commit_hash == "N/A"

def test_get_git_commit_hash_not_a_git_repo():
    """
    Tests that get_git_commit_hash returns 'N/A' when not in a git repository.
    """
    # Mock subprocess.run to raise CalledProcessError
    error = subprocess.CalledProcessError(
        returncode=128,
        cmd=["git", "rev-parse", "--short", "HEAD"],
        stderr="fatal: not a git repository"
    )
    with patch('subprocess.run', side_effect=error) as mock_run:
        commit_hash = get_git_commit_hash()

        # Assert that the function returns "N/A"
        assert commit_hash == "N/A"
