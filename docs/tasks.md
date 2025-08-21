# Self-Improving Quant Engine — Task Breakdown

This document provides a detailed, sequential list of tasks required to build the Minimum Viable Product (MVP) of the Self-Improving Quant Engine. Each task is designed to be completed in 4 hours or less and maps directly to the requirements outlined in the `prd.md` and `architecture.md` documents.

**Reviewer's Note:** This document has been updated to reflect the current state of the codebase after a significant refactoring effort to align with `HARD_RULES.md` and the project's architecture.

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
*   **Notes:**
    *   Dependencies in `requirements.txt` have been pinned to specific versions to ensure a stable, reproducible environment and resolve library conflicts.
*   **Status:** Completed

---

### Task 2 — Implement Data Service & Caching

*   **Rationale:** To create a reliable and efficient way to fetch and store historical stock data, preventing repeated API calls and ensuring data consistency across runs.
*   **Items to implement:**
    *   Create `services/data_service.py`.
    *   Implement a function `fetch_and_cache_data(ticker, years)` that caches data to a Parquet file.
*   **Status:** Completed

---

### Task 3 — Implement Baseline Strategy & Backtester

*   **Rationale:** To create the core backtesting engine and a simple, hard-coded baseline strategy (Iteration 0) that serves as the starting point for the LLM's improvements.
*   **Items to implement:**
    *   Create `core/strategy.py` to define a `backtesting.py` `Strategy` class.
    *   Implement a simple RSI Crossover strategy as the baseline.
    *   Create `core/backtester.py` (implemented as a helper function in `orchestrator.py`).
*   **Notes:**
    *   The initial implementation contained a monkey-patch for `numpy`, which violated `H-19`. This has been removed by pinning dependencies.
*   **Status:** Completed

---

### Task 4 — Implement Initial Report Generation

*   **Rationale:** To translate the raw output from the backtesting library into a structured, machine-readable JSON format that will eventually be fed to the LLM.
*   **Items to implement:**
    *   Create `core/models.py` using Pydantic to define the structure of a `Report` and `StrategyDefinition`.
    *   Logic for report generation is handled within the `Orchestrator` and `LLMService`.
*   **Notes:**
    *   A separate `ReportGenerator` service was deemed unnecessary. The functionality is integrated directly into the `Orchestrator` and the `_format_history` helper for the LLM service.
*   **Status:** Completed

---

## Epic 2: LLM-Powered Iteration Engine

*Goal: To integrate the LLM API, construct the dynamic prompt with historical context, and build the main loop that parses LLM responses to drive subsequent backtest iterations.*

---

### Task 5 — Implement Secure Strategy Parser

*   **Rationale:** To create a secure mechanism for interpreting LLM-generated strategy logic without using `eval()`, preventing arbitrary code execution vulnerabilities.
*   **Items to implement:**
    *   Create `services/parser_service.py` with a `SecureStrategyParser` class.
    *   Use `asteval` to safely evaluate buy/sell conditions in a restricted environment.
*   **Notes:**
    *   The initial implementation had this logic incorrectly placed in `strategy.py` and used `asteval` in an insecure way. This has been refactored into the `SecureStrategyParser` service, which is now used by the `Orchestrator`.
*   **Status:** Completed

---

### Task 6 — Implement LLM Service & Prompt Management

*   **Rationale:** To create a dedicated service for interacting with the LLM API, managing API keys, and constructing the prompts that guide the AI's suggestions.
*   **Items to implement:**
    *   Create `services/llm_service.py`.
    *   Implement a function to get strategy suggestions from the LLM.
    *   Create `prompts/quant_analyst.txt`.
*   **Notes:**
    *   The service now includes proper audit logging to `logs/llm_audit.jsonl` as required by `H-22`.
*   **Status:** Completed

---

### Task 7 — Implement the Core Orchestrator Loop

*   **Rationale:** To tie all the components together into the main automated feedback loop.
*   **Items to implement:**
    *   Create `core/orchestrator.py`.
    *   Implement the main `run()` function that orchestrates the services.
*   **Notes:**
    *   The `Orchestrator` has been refactored to use the `SecureStrategyParser`, ensuring a secure data flow.
*   **Status:** Completed

---

## Epic 3: CLI & Operational Polish

*Goal: To wrap the system in a user-friendly CLI, implement robust error handling, add secure API key management, and ensure clear logging and final reporting.*

---

### Task 8 — Implement State Manager for Resumability

*   **Rationale:** To make the system robust against interruptions.
*   **Items to implement:**
    *   Create `services/state_manager.py` for saving/loading run state.
    *   Integrate state management into the `Orchestrator`.
*   **Status:** Completed

---

### Task 9 — Implement Train/Validation Split & Final Validation

*   **Rationale:** To combat overfitting and provide a more honest assessment of a strategy's performance.
*   **Items to implement:**
    *   Split data into training and validation sets in `DataService`.
    *   Use training data in the main loop and validation data for the final report in the `Orchestrator`.
*   **Status:** Completed

---

### Task 10 — Enhance to Rich Report & Edge Score

*   **Rationale:** To improve the quality of the feedback signal given to the LLM.
*   **Items to implement:**
    *   Calculate a custom "Edge Score" in the `Orchestrator`.
    *   Update Pydantic models in `core/models.py`.
*   **Status:** Completed

---

### Task 11 — Implement CLI, Logging, and Final Output

*   **Rationale:** To create the primary user interface for the tool.
*   **Items to implement:**
    *   Use `argparse` in `main.py` for CLI arguments.
    *   Set up a centralized logger in `utils/logging_config.py`.
*   **Notes:**
    *   The initial implementation used a basic logger. This has been refactored to use the centralized configuration.
*   **Status:** Completed

---

### Task 12 — Implement Robustness & Cost Management Features

*   **Rationale:** To make the system production-ready by handling common failures gracefully and providing visibility into operational costs.
*   **Items to implement:**
    *   Add features for robustness (timeouts, retries) and cost management (context summarization).
*   **Status:** Not Started
