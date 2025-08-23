#!/usr/bin/env python
"""
A simple runner script for the Praxis Engine.
"""
import os

def main():
    """
    Runs the backtest command with default settings.
    """
    os.system("python -m praxis_engine.main backtest")

if __name__ == "__main__":
    main()
