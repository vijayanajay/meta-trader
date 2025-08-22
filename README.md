# Self-Improving Quant Engine

This project is a CLI tool that uses a Large Language Model (LLM) to iteratively discover and optimize quantitative trading strategies.

The core architecture is built around a deterministic backtesting engine with a constrained set of indicators and logic. The LLM acts as an intelligent parameter selector, proposing new strategy configurations in a safe and structured JSON format.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/example/repo.git
    cd self-improving-quant-engine
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install the project in editable mode:**
    This step is crucial. It creates a special link to your source code (`src`) so that when you run `python src/main.py`, the Python interpreter can find your project's modules (e.g., `core`, `services`). Without this, absolute imports like `from core.orchestrator import Orchestrator` would fail because the `src` directory is not automatically in Python's path. Editable mode solves this by making the project importable everywhere in your environment.
    ```bash
    pip install -e .
    ```

5.  **Configure your environment:**
    -   Copy the `.env.example` file to `.env`:
        ```bash
        cp .env.example .env
        ```
    -   Edit the `.env` file and add your `OPENROUTER_API_KEY`.

## Execution

The application is configured via `config.ini` for general settings and `.env` for secrets like API keys. The `LLMService` will use the provider and model details specified in your `.env` file.

To run the application, execute the main script from the root of the project:

```bash
python src/main.py
```

This will start the engine, which will:
1.  Load the configuration from `config.ini` and `.env`.
2.  Initialize all the necessary services.
3.  Instantiate the Orchestrator.
4.  Begin the strategy optimization loop based on the parameters in `config.ini`.

Console output will show the progress of the run. Final results and reports will be saved to the `results/` directory.
