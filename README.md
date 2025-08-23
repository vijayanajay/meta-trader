# "Praxis" - An Indian Market Mean-Reversion Engine

This project is a quantitative trading system designed to identify and capitalize on high-probability mean-reversion opportunities within the Indian stock market (NSE).

The system's core philosophy is not to predict prices, but to apply a cascade of statistical and market-regime filters to isolate asymmetric risk-reward scenarios. It leverages a minimal, locally-hosted LLM not as a predictive oracle, but as a final statistical auditor.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd praxis-engine
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    The project uses Poetry for dependency management. If you don't have Poetry, you can install it following the official instructions. Once Poetry is installed, run:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install the project in editable mode:**
    This step is crucial. It makes the `praxis_engine` package importable throughout your environment, so the CLI and tests can find the modules.
    ```bash
    pip install -e .
    ```

5.  **Configure your environment:**
    The project uses an `.env` file for API keys.
    -   Copy the `.env.example` file to `.env`:
        ```bash
        cp .env.example .env
        ```
    -   Edit the `.env` file and add your `OPENROUTER_API_KEY` if you plan to use the LLM features.

## Verification

The primary configuration is in `praxis_engine/config.ini`. To verify that your setup is correct and the configuration is valid, you can run the `verify-config` command.

```bash
# Note: There is a known issue with Typer's command invocation.
# This command may not work as expected until Task 1.1 is completed.
python -m praxis_engine.main verify-config
```

This will load and validate the configuration, printing the results to the console.

Final results and reports will be saved to the `results/` directory.
