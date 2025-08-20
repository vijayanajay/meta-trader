
# Self-Improving Quant Engine — Task Breakdown

This document provides a detailed, sequential list of tasks required to build the Minimum Viable Product (MVP) of the Self-Improving Quant Engine. Each task is designed to be completed in 4 hours or less and maps directly to the requirements outlined in the `prd.md` and `architecture.md` documents.

## Epic 1: Core Backtesting Pipeline

*Goal: To build a non-iterative pipeline that can fetch data for one stock, apply a hard-coded baseline strategy, run a backtest, and generate a performance report. This validates the core quantitative components.*

---

### Task 1 — Project Scaffolding & Dependency Setup

*   **Rationale:** Establish a clean, reproducible project structure and environment. This is the foundation for all subsequent development.
*   **Items to implement:**
    *   Create the directory structure as defined in `architecture.md`.
    *   Initialize a Git repository.
    *   Create `pyproject.toml` and a `requirements.txt` file.
    *   Add core dependencies: `pandas`, `pandas-ta`, `backtesting.py`, `yfinance`, `python-dotenv`.
    *   Create `.env.example` for environment variable management.
    *   Create the CLI entry point `main.py` with a placeholder function.
*   **Tests to cover:**
    *   N/A. This is a setup task.
*   **Acceptance Criteria (AC):**
    *   The project structure matches the architecture document.
    *   Dependencies can be installed successfully using `pip install -r requirements.txt`.
*   **Definition of Done (DoD):**
    *   The initial project structure is committed to the repository.
*   **Time estimate:** 1 hour
*   **Status:** Completed

---

### Task 2 — Implement Data Service & Caching

*   **Rationale:** To create a reliable and efficient way to fetch and store historical stock data, preventing repeated API calls and ensuring data consistency across runs.
*   **Items to implement:**
    *   Create `services/data_service.py`.
    *   Implement a function `fetch_and_cache_data(ticker, years)` that:
        *   Checks if a `data/stock_data.parquet` file exists. If so, loads it.
        *   If not, uses `yfinance` to download 10 years of daily data for the given ticker.
        *   Saves the downloaded DataFrame to `data/stock_data.parquet`.
    *   For now, this service will return the full DataFrame. The train/validation split will be added in a later task.
*   **Tests to cover:**
    *   Create `tests/test_data_service.py`.
    *   Add a test that mocks `yfinance.download` and verifies that the service saves a Parquet file.
    *   Add a test that verifies the service loads data from the cache file if it exists.
*   **Acceptance Criteria (AC):**
    *   The `DataService` can successfully download and save data.
    *   Subsequent calls for the same ticker use the cached file.
*   **Definition of Done (DoD):**
    *   `data_service.py` and its unit tests are implemented and committed.
*   **Time estimate:** 2.5 hours
*   **Status:** Not Started

---

### Task 3 — Implement Baseline Strategy & Backtester

*   **Rationale:** To create the core backtesting engine and a simple, hard-coded baseline strategy (Iteration 0) that serves as the starting point for the LLM's improvements.
*   **Items to implement:**
    *   Create `core/strategy.py` to define a `backtesting.py` `Strategy` class.
    *   Implement a simple RSI Crossover strategy (e.g., buy when RSI(14) < 30, sell when RSI(14) > 70).
    *   Create `core/backtester.py`.
    *   Implement a function `run_backtest(data, strategy_class)` that initializes and runs `backtesting.py`'s `Backtest` object.
    *   The function should return the results object from `backtesting.py`.
*   **Tests to cover:**
    *   Create `tests/test_backtester.py`.
    *   Add a test that runs the backtester with sample data and the baseline strategy, asserting that a results object is returned without errors.
*   **Acceptance Criteria (AC):**
    *   A backtest can be executed programmatically on a pandas DataFrame.
    *   The baseline RSI strategy is correctly defined.
*   **Definition of Done (DoD):**
    *   `strategy.py`, `backtester.py`, and their tests are implemented and committed.
*   **Time estimate:** 2 hours
*   **Status:** Not Started

---

### Task 4 — Implement Initial Report Generation

*   **Rationale:** To translate the raw output from the backtesting library into a structured, machine-readable JSON format that will eventually be fed to the LLM.
*   **Items to implement:**
    *   Create `core/models.py` using Pydantic to define the structure of a `Report` and `StrategyDefinition`.
    *   Create a `ReportGenerator` component (e.g., in `services/report_service.py`).
    *   Implement a function `generate_report(backtest_results, strategy_definition)` that extracts key metrics (Sharpe Ratio, Max Drawdown, Return [%]) from the `backtesting.py` results.
    *   The function should return a structured JSON object (or a Pydantic model instance) matching the initial report structure.
*   **Tests to cover:**
    *   Create `tests/test_report_service.py`.
    *   Add a test that passes a mock `backtesting.py` results object and verifies the generated JSON report has the correct structure and values.
*   **Acceptance Criteria (AC):**
    *   A structured JSON report is generated from a backtest run.
*   **Definition of Done (DoD):**
    *   The report generation module and its tests are implemented and committed.
*   **Time estimate:** 2 hours
*   **Status:** Not Started

---

## Epic 2: LLM-Powered Iteration Engine

*Goal: To integrate the LLM API, construct the dynamic prompt with historical context, and build the main loop that parses LLM responses to drive subsequent backtest iterations.*

---

### Task 5 — Implement Secure Strategy Parser

*   **Rationale:** To create a secure mechanism for interpreting LLM-generated strategy logic without using `eval()`, preventing arbitrary code execution vulnerabilities. This is a critical security requirement.
*   **Items to implement:**
    *   Create `services/parser_service.py`.
    *   Add `asteval` to `requirements.txt`.
    *   Implement a function `parse_strategy(llm_json_response)` that:
        *   Loads the JSON string.
        *   Validates the presence of `indicators`, `buy_signal`, and `sell_signal`.
        *   Returns a validated strategy definition object (e.g., a Pydantic model).
    *   Implement a separate function `evaluate_signal(signal_string, data_frame)` that uses `asteval` to safely evaluate the buy/sell conditions against the columns of a pandas DataFrame.
*   **Tests to cover:**
    *   Create `tests/test_parser_service.py`.
    *   Test with valid JSON for a simple SMA crossover.
    *   Test with malformed JSON to ensure it fails gracefully.
    *   Test `evaluate_signal` with a sample DataFrame to ensure it correctly returns a boolean series.
    *   Test with a malicious string (e.g., `__import__('os').system('rm -rf /')`) to ensure `asteval` prevents execution.
*   **Acceptance Criteria (AC):**
    *   The parser can successfully convert a valid LLM JSON response into an executable strategy definition.
    *   The parser rejects invalid or malicious inputs.
*   **Definition of Done (DoD):**
    *   `parser_service.py` and its comprehensive tests are implemented and committed.
*   **Time estimate:** 3.5 hours
*   **Status:** Not Started

---

### Task 6 — Implement LLM Service & Prompt Management

*   **Rationale:** To create a dedicated service for interacting with the LLM API, managing API keys, and constructing the prompts that guide the AI's suggestions.
*   **Items to implement:**
    *   Create `services/llm_service.py`.
    *   Add a dependency for an LLM client library (e.g., `openai`).
    *   Implement a function `get_strategy_suggestion(history: list[dict])` that:
        *   Loads the LLM API key from environment variables.
        *   Loads the base prompt from `prompts/quant_analyst.txt`.
        *   Formats the `history` of previous reports into a string.
        *   Constructs the final prompt and sends it to the LLM API.
        *   Returns the raw JSON string from the LLM response.
    *   Create the initial `prompts/quant_analyst.txt` file with instructions for the LLM to act as a quant and return JSON.
*   **Tests to cover:**
    *   Create `tests/test_llm_service.py`.
    *   Add a test that mocks the LLM API client and verifies the service constructs the correct prompt string from a sample history.
*   **Acceptance Criteria (AC):**
    *   The service can send a well-formatted prompt to the LLM API.
    *   API keys are handled securely via environment variables.
*   **Definition of Done (DoD):**
    *   `llm_service.py`, the initial prompt file, and tests are implemented and committed.
*   **Time estimate:** 2.5 hours
*   **Status:** Not Started

---

### Task 7 — Implement the Core Orchestrator Loop

*   **Rationale:** To tie all the components together into the main automated feedback loop, orchestrating the flow from backtesting to LLM suggestion to the next iteration.
*   **Items to implement:**
    *   Create `core/orchestrator.py`.
    *   Implement the main `run()` function that takes the number of iterations as an argument.
    *   Inside a `for` loop:
        1.  Run the backtest for the current strategy.
        2.  Generate a report for the backtest.
        3.  Append the report to the history list.
        4.  Call the `LLMService` with the full history to get a new suggestion.
        5.  Call the `SecureStrategyParser` to parse the suggestion into the next strategy.
    *   The loop should start with the hard-coded baseline strategy for Iteration 0.
*   **Tests to cover:**
    *   Create `tests/test_orchestrator.py`.
    *   This will be an integration test. Mock the `LLMService` to return a predictable sequence of valid strategy JSONs.
    *   Assert that the orchestrator completes the specified number of iterations without crashing.
*   **Acceptance Criteria (AC):**
    *   The system can run a multi-iteration loop automatically.
    *   Each component is called in the correct sequence.
*   **Definition of Done (DoD):**
    *   `orchestrator.py` and its integration test are implemented and committed.
*   **Time estimate:** 4 hours
*   **Status:** Not Started

---

## Epic 3: CLI & Operational Polish

*Goal: To wrap the system in a user-friendly CLI, implement robust error handling, add secure API key management, and ensure clear logging and final reporting.*

---

### Task 8 — Implement State Manager for Resumability

*   **Rationale:** To make the system robust against interruptions (e.g., crashes, network errors). The state manager ensures that a long run can be resumed from the last completed iteration, saving time and money.
*   **Items to implement:**
    *   Create `services/state_manager.py`.
    *   Implement `save_state(history)` which writes the list of all reports to `run_state.json`.
    *   Implement `load_state()` which reads and returns the history from `run_state.json`, or returns an empty list if the file doesn't exist.
    *   In `core/orchestrator.py`:
        *   Call `load_state()` at the beginning of a run.
        *   Call `save_state()` at the end of each successful iteration inside the loop.
*   **Tests to cover:**
    *   Create `tests/test_state_manager.py`.
    *   Test saving a sample history and then loading it to ensure the data is identical.
    *   Test loading when the file does not exist.
*   **Acceptance Criteria (AC):**
    *   The run state is persisted to disk after every iteration.
    *   The orchestrator can resume a run from a previously saved state.
*   **Definition of Done (DoD):**
    *   `state_manager.py` and its tests are implemented and integrated into the orchestrator.
*   **Time estimate:** 2 hours
*   **Status:** Completed

---

### Task 9 — Implement Train/Validation Split & Final Validation

*   **Rationale:** To combat overfitting and provide a more honest assessment of a strategy's performance. This is a critical step for ensuring the discovered strategies are generalizable.
*   **Items to implement:**
    *   In `services/data_service.py`, modify the data fetching function to split the 10 years of data into an 8-year training set and a 2-year validation set. It should return both DataFrames.
    *   In `core/orchestrator.py`, ensure the main iteration loop *only* uses the **training set**.
    *   After the loop completes, implement the "Final Validation" logic:
        1.  Select the top 3-5 strategies from the history based on their performance on the training data.
        2.  Run a backtest for each of these top strategies on the unseen **validation set**.
        3.  Identify and report the best-performing strategy on the validation data.
*   **Tests to cover:**
    *   Update `tests/test_data_service.py` to verify the data is split correctly into two non-overlapping DataFrames of the expected length.
*   **Acceptance Criteria (AC):**
    *   The LLM's learning loop is confined to the training data.
    *   The final output of the system is based on performance on the unseen validation data.
*   **Definition of Done (DoD):**
    *   The data split and final validation logic are implemented and committed.
*   **Time estimate:** 3 hours
*   **Status:** Completed

---

### Task 10 — Enhance to Rich Report & Edge Score

*   **Rationale:** To improve the quality of the feedback signal given to the LLM. A richer report with a custom score and details on failures provides more context, enabling the LLM to make more intelligent suggestions.
*   **Items to implement:**
    *   In the `ReportGenerator` service:
        *   Calculate a custom "Edge Score" using the formula: `(Net Profit % / Exposure Time %) * (abs(Sharpe Ratio) / abs(Sortino Ratio))`.
        *   Extract details of the 5 worst trades (e.g., largest drawdowns) from the backtest results.
        *   Add these new fields (`edge_score`, `worst_trades`) to the JSON report structure.
    *   Update the Pydantic models in `core/models.py`.
    *   In `core/orchestrator.py`, update the final validation logic to use the `Edge Score` for ranking strategies.
*   **Tests to cover:**
    *   Update `tests/test_report_service.py` to verify the new fields are correctly calculated and included in the report.
*   **Acceptance Criteria (AC):**
    *   The JSON report sent to the LLM contains the Edge Score and worst trade details.
    *   The final strategy selection is based on the Edge Score.
*   **Definition of Done (DoD):**
    *   The report generator is updated and tested.
*   **Time estimate:** 3 hours
*   **Status:** Completed

---

### Task 11 — Implement CLI, Logging, and Final Output

*   **Rationale:** To create the primary user interface for the tool, providing clear feedback during a run and presenting the final results in a human-readable format.
*   **Items to implement:**
    *   In `main.py`, use `argparse` or `click` to create a CLI that accepts arguments like `--ticker` and `--iterations`.
    *   Set up a centralized logger in `utils/logging_config.py`.
    *   Throughout the application (Orchestrator, services), add clear log messages for key stages (e.g., "Fetching data...", "Running backtest for Iteration 3...", "Awaiting LLM response...").
    *   In the `Orchestrator`, after the final validation step, print a clean, formatted summary of the best strategy found and its performance on both the train and validation sets.
*   **Tests to cover:**
    *   N/A for direct CLI testing, but manual testing is required.
*   **Acceptance Criteria (AC):**
    *   The application can be started from the command line with parameters.
    *   The console provides real-time status updates.
    *   A clear summary report is printed upon completion.
*   **Definition of Done (DoD)::**
    *   The CLI and logging are implemented, and a full run can be initiated and monitored from the command line.
*   **Time estimate:** 2.5 hours
*   **Status:** Not Started

---

### Task 12 — Implement Robustness & Cost Management Features

*   **Rationale:** To make the system production-ready by handling common failures gracefully and providing visibility into operational costs.
*   **Items to implement:**
    *   In `core/backtester.py`, add a timeout to the backtest execution to prevent runaway calculations from bad LLM suggestions.
    *   In `services/llm_service.py`:
        *   Add basic retry logic (e.g., exponential backoff) for API calls.
        *   Log the prompt and completion token count for every API call to the console.
        *   (Optional, if time permits) Implement a simple context summarization: if `history` has >10 reports, replace the oldest 5 with a single summary entry.
    *   In `services/parser_service.py`, add error handling for when the LLM returns syntactically incorrect JSON, marking the iteration as a failure and continuing.
*   **Tests to cover:**
    *   Add a test in `tests/test_parser_service.py` for malformed JSON.
*   **Acceptance Criteria (AC):**
    *   The system does not crash on transient API errors or invalid LLM responses.
    *   Backtests with excessive computation time are terminated.
    *   LLM token usage is visible to the user.
*   **Definition of Done (DoD):**
    *   Error handling, timeouts, and cost logging are implemented.
*   **Time estimate:** 4 hours
*   **Status:** Not Started