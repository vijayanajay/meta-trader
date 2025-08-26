"""
Main entry point for the Praxis Engine application.

This script is responsible for:
1. Loading environment variables from the .env file.
2. Setting up the Typer CLI application.
"""
from pathlib import Path
import typer
from dotenv import load_dotenv

# --- Application Startup ---
# Load environment variables FIRST, before any application code is imported.
# Explicitly provide the path to the .env file to avoid ambiguity.
dotenv_path = Path('.env')
load_dotenv(dotenv_path=dotenv_path)

# Import the application's CLI module AFTER loading the environment.
from praxis_engine import main as cli_main

# The `app` object in `cli_main` is the Typer application.
app = cli_main.app

if __name__ == "__main__":
    app()
