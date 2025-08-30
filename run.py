#!/usr/bin/env python
import sys
from pathlib import Path

# Add the project root to the python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from praxis_engine.main import app

if __name__ == "__main__":
    app()
