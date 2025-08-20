from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from self_improving_quant.core.models import IterationReport

__all__ = ["save_state", "load_state"]

logger = logging.getLogger(__name__)


# impure
def save_state(history: list[IterationReport], file_path: Path | str = "run_state.json") -> None:
    """Saves the history of iteration reports to a JSON file."""
    logger.info(f"Saving run state to {file_path}...")
    try:
        # We need to use model_dump_json to handle Pydantic models correctly
        json_str = json.dumps([report.model_dump() for report in history], indent=2)
        Path(file_path).write_text(json_str)
    except (TypeError, IOError) as e:
        logger.error(f"Failed to save state: {e}")


# impure
def load_state(file_path: Path | str = "run_state.json") -> list[IterationReport]:
    """Loads the history of iteration reports from a JSON file."""
    path = Path(file_path)
    if not path.exists():
        logger.info("No saved state file found. Starting a new run.")
        return []

    logger.info(f"Loading run state from {file_path}...")
    try:
        with path.open("r") as f:
            raw_data = json.load(f)

        # Validate each object in the list
        history = [IterationReport.model_validate(item) for item in raw_data]
        logger.info(f"Successfully loaded {len(history)} previous iterations.")
        return history
    except (IOError, json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to load or validate state file: {e}. Starting a new run.")
        return []
