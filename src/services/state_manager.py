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
    Handles saving and loading of the application's run state,
    enabling resumability.
    """

    def __init__(self, state_filepath: Path):
        """
        Initializes the StateManager.

        Args:
            state_filepath: The path to the JSON file where the state is stored.
        """
        self._state_filepath = state_filepath

    # impure
    def save_state(self, run_state: RunState) -> None:
        """
        Saves the given RunState to the state file atomically.

        Args:
            run_state: The RunState object to save.
        """
        # Use a temporary file and atomic rename to prevent corruption
        temp_dir = self._state_filepath.parent
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', delete=False, dir=temp_dir, suffix='.tmp'
            ) as f:
                temp_path = Path(f.name)
                f.write(run_state.model_dump_json(indent=4))

            temp_path.rename(self._state_filepath)
        except Exception as e:
            # If something goes wrong, try to clean up the temp file
            if temp_path and temp_path.exists():
                temp_path.unlink()
            raise e

    # impure
    def load_state(self) -> RunState:
        """
        Loads the RunState from the state file.

        If the file does not exist, it returns a new RunState object,
        representing the start of a new run.

        If the file is corrupted, it raises a ValueError.

        Returns:
            The loaded or a new RunState object.
        """
        if not self._state_filepath.exists():
            return RunState(iteration_number=0, history=[])

        try:
            with open(self._state_filepath, 'r') as f:
                data = json.load(f)
            return RunState.model_validate(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding state file: {self._state_filepath}") from e
        except Exception as e:
            # Catches Pydantic validation errors and other issues
            raise ValueError(f"Error loading state file: {self._state_filepath}") from e
