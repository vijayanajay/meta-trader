"""
Service for managing the state of an optimization run.
"""
import json
import tempfile
from pathlib import Path
from typing import Optional

from core.models import RunState

__all__ = ["StateManager"]


class StateManager:
    """
    Handles saving and loading of the application's run state for each ticker,
    enabling resumability.
    """

    def __init__(self, results_dir: str, run_state_file: str):
        """
        Initializes the StateManager.

        Args:
            results_dir: The base directory where results are stored.
            run_state_file: The filename template for the state file.
        """
        self._results_dir = Path(results_dir)
        self._run_state_file = run_state_file
        self._results_dir.mkdir(parents=True, exist_ok=True)

    def _get_state_filepath(self, ticker: str) -> Path:
        """Constructs the full path to the state file for a given ticker."""
        return self._results_dir / f"{ticker}_{self._run_state_file}"

    # impure
    def save_state(self, ticker: str, run_state: RunState) -> None:
        """
        Saves the given RunState to the ticker's state file atomically.

        Args:
            ticker: The ticker symbol.
            run_state: The RunState object to save.
        """
        state_filepath = self._get_state_filepath(ticker)
        temp_dir = state_filepath.parent
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', delete=False, dir=temp_dir, suffix='.tmp'
            ) as f:
                temp_path = Path(f.name)
                f.write(run_state.model_dump_json(indent=4))

            temp_path.rename(state_filepath)
        except Exception as e:
            if temp_path and temp_path.exists():
                temp_path.unlink()
            raise e

    # impure
    def load_state(self, ticker: str) -> RunState:
        """
        Loads the RunState from the ticker's state file.

        If the file does not exist, it returns a new RunState object.
        If the file is corrupted, it raises a ValueError.

        Args:
            ticker: The ticker symbol.

        Returns:
            The loaded or a new RunState object.
        """
        state_filepath = self._get_state_filepath(ticker)
        if not state_filepath.exists():
            return RunState(iteration_number=0, history=[])

        try:
            with open(state_filepath, 'r') as f:
                data = json.load(f)
            return RunState.model_validate(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding state file: {state_filepath}") from e
        except Exception as e:
            raise ValueError(f"Error loading state file: {state_filepath}") from e
