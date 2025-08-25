#!/usr/bin/env python
"""
A simple runner script for the Praxis Engine.
"""
from praxis_engine.main import app

def main() -> None:
    """
    Runs the backtest command with default settings.
    """
    app()

if __name__ == "__main__":
    main()
