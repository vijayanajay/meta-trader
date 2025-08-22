# Self-Improving Quant Engine — Task Breakdown

This document provides a detailed, sequential list of tasks required to build the Minimum Viable Product (MVP) of the Self-Improving Quant Engine. Each task is designed to be completed in 4 hours or less and maps directly to the requirements outlined in the `prd.md`, `architecture.md`, and `HARD_RULES.md` documents.

## Epic 1: Core Backtesting Pipeline & Foundation

*Goal: To build a non-iterative, deterministic pipeline that can be executed programmatically. This epic focuses on creating the core components that can take a hard-coded strategy, run it on historical data, and produce a structured report, all without any LLM interaction.*

---

### Task 1 — Project Scaffolding & Configuration Service

*   **Rationale:** Establish a clean, reproducible project structure and a centralized configuration system, adhering to architectural and quality standards from the outset.
*   **Items to implement:**
    *   Create the directory structure as defined in `architecture.md`.
    *   Initialize a Git repository with a `.gitignore` file.
    *   Create `pyproject.toml` to define the project and configure tools like `mypy`.
    *   Create `requirements.txt` with initial dependencies (`pandas`, `python-dotenv`, `configparser`, `pytest`, `mypy`, `pandas-stubs`).
    *   Create `.env.example` for API keys (H-15).
    *   Create `config.ini` with placeholder values for tickers, iterations, and file paths (H-16).
    *   Implement `services/config_service.py` to load and parse `config.ini`.
    *   Implement `core/models.py` with a Pydantic model for the configuration object to ensure type safety.
    *   Create the CLI entry point `main.py` that loads the config and prints it.
    *   Create placeholder classes for all core components (`Orchestrator`, `LLMService`, etc.).
*   **Tests to cover:**
    *   Create `tests/test_config_service.py`.
    *   Test that the service correctly parses a sample `config.ini` into the Pydantic model.
    *   Test that it raises an error for missing required sections or keys.
*   **Acceptance Criteria (AC):**
    *   The project structure matches `architecture.md`.
    *   The project is installable in editable mode (`pip install -e .`).
    *   Running `python src/main.py` successfully initializes all components.
    *   Code passes `mypy --strict` (H-1) and all `pytest` checks.
*   **Definition of Done (DoD):**
    *   The initial project structure and configuration service are committed to the repository.
*   **Time estimate:** 2 hours
*   **Status:** Not Started

---

### Task 1.5 — Refine Project Setup & Add Developer Guide

*   **Rationale:** To prevent recurring setup and import path issues by documenting the correct development environment setup and project structure conventions. This improves developer onboarding and reduces debugging time.
*   **Items to implement:**
    *   Create a `CONTRIBUTING.md` or update `README.md` with a "Developer Setup" section.
    *   The guide must specify:
        *   The requirement to use a virtual environment.
        *   The command to install dependencies: `pip install -r requirements.txt`.
        *   The command to install the project in editable mode: `pip install -e .`.
        *   A clear explanation of why editable mode is necessary for the import paths (`from services...` not `from src.services...`) to work correctly.
*   **Acceptance Criteria (AC):**
    *   A developer can follow the guide to set up the project and run tests successfully without encountering import errors.
*   **Definition of Done (DoD):**
    *   The developer setup guide is written and committed.
*   **Time estimate:** 1 hour
*   **Status:** Completed

---

### Task 2 — Implement Data Service with Caching & Splitting

*   **Rationale:** To create a reliable and efficient service for fetching, caching, and splitting historical stock data, preventing repeated API calls and strictly enforcing the train/validation data separation.
*   **Items to implement:**
    *   Add `yfinance` and `pyarrow` to `requirements.txt`.
    *   Create `services/data_service.py` (H-6, H-7).
    *   Implement a `DataService` class with a method `get_data(ticker)` that:
        *   Checks for a local Parquet cache file.
        *   If cache is missing, uses `yfinance` to download 10 years of daily data. This function must be marked `# impure` (H-8).
        *   Saves the downloaded DataFrame to the cache.
        *   Deterministically splits the data into an 8-year training set and a 2-year validation set (FR2).
        *   Returns both DataFrames.
*   **Tests to cover:**
    *   Create `tests/test_data_service.py`.
    *   Mock `yfinance.download` to test caching logic without network calls.
    *   Verify that the data split is correct (e.g., correct date ranges, no overlap).
*   **Acceptance Criteria (AC):**
    *   The `DataService` can download and save data.
    *   Subsequent calls use the cached file.
    *   The service correctly returns two distinct `train` and `validation` DataFrames (H-19).
*   **Definition of Done (DoD):**
    *   `data_service.py` and its unit tests are implemented and pass `mypy --strict`.
*   **Time estimate:** 2.5 hours
*   **Status:** Completed

---

### Task 3 — Implement Baseline Strategy & Backtester Wrapper

*   **Rationale:** To create the core backtesting engine and a simple, hard-coded baseline strategy (Iteration 0) that serves as a reproducible benchmark for all future improvements.
*   **Items to implement:**
    *   Add `backtesting.py` to `requirements.txt`.
    *   Create `core/strategy.py` to define a `backtesting.py` `Strategy` class.
    *   Implement the hard-coded SMA Crossover baseline strategy as defined in the PRD (FR8, H-21).
    *   Create `services/backtester.py`.
    *   Implement a `Backtester` service with a `run(data, strategy_class)` method that initializes and runs `backtesting.py`'s `Backtest` object.
    *   The function must return the results object from `backtesting.py`.
*   **Tests to cover:**
    *   Create `tests/test_backtester.py`.
    *   Add a test that runs the backtester with sample data and the baseline strategy, asserting that a results object is returned without errors.
*   **Acceptance Criteria (AC):**
    *   A backtest can be executed programmatically on a pandas DataFrame.
    *   The baseline SMA Crossover strategy is correctly defined.
*   **Definition of Done (DoD):**
    *   `strategy.py`, `backtester.py`, and their tests are implemented and committed.
*   **Time estimate:** 2 hours
*   **Status:** Completed

---

### Task 4 — Implement Report Generator

*   **Rationale:** To translate the raw output from the backtesting library into the information-dense, structured JSON format required by the PRD, which will serve as the learning signal for the LLM.
*   **Items to implement:**
    *   In `core/models.py`, define Pydantic models for `StrategyDefinition`, `TradeSummary`, and `PerformanceReport` as specified in FR4.
    *   Create `services/report_generator.py`.
    *   Implement a `ReportGenerator` service with a method `generate(backtest_results, strategy_definition)` that:
        *   Extracts all required metrics (Sharpe, Sortino, Max Drawdown, etc.).
        *   Calculates the "Information-Dense Statistical Trade Summary" (FR4).
        *   Populates and returns a `PerformanceReport` Pydantic model instance.
*   **Tests to cover:**
    *   Create `tests/test_report_generator.py`.
    *   Pass a mock `backtesting.py` results object and verify the generated report model has the correct structure and values.
*   **Acceptance Criteria (AC):**
    *   A structured, typed report object is generated from a backtest run.
    *   All metrics from FR4 are present and correctly calculated.
*   **Definition of Done (DoD):**
    *   The report generation module and its tests are implemented and committed.
*   **Time estimate:** 2.5 hours
*   **Status:** Completed

---

### Task 4.1 — Fix Core Pipeline Integrity

*   **Rationale:** The core pipeline of Epic 1 is broken. The `Backtester` service has an incorrect interface that does not provide the `trades` data required by the `ReportGenerator`. This task is critical to making Epic 1 functional.
*   **Items to implement:**
    *   Modify `services/backtester.py`: The `run()` method must return a tuple of `(stats, trades)`.
    *   Update `tests/test_backtester.py` to reflect the new return type.
    *   Update `services/report_generator.py`: Ensure the `generate()` method correctly receives and uses the `trades` DataFrame.
*   **Acceptance Criteria (AC):**
    *   The `Backtester` and `ReportGenerator` services can be chained together successfully.
    *   A complete `PerformanceReport`, including the `TradeSummary`, can be generated from a backtest run.
*   **Definition of Done (DoD):**
    *   The interface bug is fixed and verified with an integration test.
*   **Time estimate:** 1.5 hours
*   **Status:** Completed

---

### Task 4.2 — Enforce Code Quality Gates

*   **Rationale:** The project currently fails its own quality gate (`mypy --strict`), violating `H-1`. This must be fixed to maintain code quality and ensure the reliability of the experimental framework.
*   **Items to implement:**
    *   Add `pandas-stubs` to `requirements.txt` to ensure correct type checking for `pandas`.
    *   Add type hints (`-> None`) to all test functions in `tests/` to make them compliant with `mypy --strict`.
*   **Acceptance Criteria (AC):**
    *   Running `mypy --strict .` from the project root passes with zero errors.
*   **Definition of Done (DoD):**
    *   All type errors are resolved.
*   **Time estimate:** 1 hour
*   **Status:** Completed

---

### Task 4.3 — Refactor Premature Abstractions

*   **Rationale:** The codebase contains numerous placeholder files and premature orchestration logic in `main.py`, violating the MVP-first approach (`H-5`, `H-26`). This adds clutter and misrepresents the project's true progress.
*   **Items to implement:**
    *   **Delete** the following placeholder files: `core/orchestrator.py`, `services/llm_service.py`, `services/strategy_engine.py`, `services/state_manager.py`.
    *   **Refactor** `src/main.py` to be a simple script that only validates the functionality of Epic 1 (i.e., runs the baseline strategy and generates a report). Remove all references to the deleted services.
*   **Acceptance Criteria (AC):**
    *   The `src` directory is clean and contains only the code necessary for a functional Epic 1.
    *   `python src/main.py` runs without error.
*   **Definition of Done (DoD):**
    *   All placeholder files are deleted and `main.py` is refactored.
*   **Time estimate:** 1 hour
*   **Status:** Completed

---

### Task 4.5 — Document Mypy Setup and Typing Best Practices

*   **Rationale:** To solidify the project's commitment to static typing and prevent future developers from struggling with the same `mypy --strict` issues that were resolved during Task 4. This captures important institutional knowledge.
*   **Items to implement:**
    *   Create a new section in `README.md` or a new `docs/typing_guide.md` file.
    *   Document the `mypy` configuration in `pyproject.toml`, explaining why overrides for libraries like `backtesting` and `pandas-ta` are necessary.
    *   Provide a clear example of how to handle untyped return values from these libraries using `typing.cast`.
    *   Explain the `# type: ignore[misc]` comment used in `strategy.py` for subclassing untyped classes, and when it is appropriate to use it.
*   **Acceptance Criteria (AC):**
    *   A developer can read the guide and understand how to work with the strict `mypy` environment without needing to re-discover the solutions for common third-party library issues.
*   **Definition of Done (DoD):**
    *   The typing guide is written and committed.
*   **Time estimate:** 1 hour
*   **Status:** Completed

---

## Epic 2: LLM-Powered Iteration Engine

*Goal: To integrate the LLM, construct the dynamic prompt with historical context, and build the main loop that securely parses LLM responses to drive subsequent backtest iterations.*

---

### Task 5 — Implement Secure Strategy Engine with `asteval`

*   **Rationale:** To create a secure mechanism for interpreting LLM-generated strategy logic without using `eval()`, preventing arbitrary code execution. This is the cornerstone of the system's security architecture.
*   **Items to implement:**
    *   Add `asteval` and `pandas-ta` to `requirements.txt`.
    *   Create `services/strategy_engine.py`.
    *   Implement a `StrategyEngine` service with a method `process(data, strategy_def)` that:
        *   Iterates through the `indicators` list in the strategy definition, calculating them using `pandas-ta` and adding them as columns to the data.
        *   Uses `asteval` to safely evaluate the `buy_condition` and `sell_condition` strings against the DataFrame columns, generating the final signal series.
        *   Returns a new `backtesting.py` `Strategy` class dynamically created with the evaluated signals.
*   **Tests to cover:**
    *   Create `tests/test_strategy_engine.py`.
    *   Test with a valid JSON for a simple EMA crossover.
    *   Test `asteval` with a malicious string (e.g., `__import__('os').system('rm -rf /')`) to ensure it fails safely (H-14).
    *   Test with a condition that references a non-existent indicator to ensure it fails gracefully.
*   **Acceptance Criteria (AC):**
    *   The engine can convert a valid strategy definition into an executable `backtesting.py` strategy.
    *   The engine rejects invalid or malicious inputs without executing them.
*   **Definition of Done (DoD):**
    *   `strategy_engine.py` and its comprehensive security tests are implemented and committed.
*   **Time estimate:** 3.5 hours
*   **Status:** Completed

---

### Task 5.1 — Integrate Strategy Engine into Main Workflow

*   **Rationale:** The `StrategyEngine` has been implemented, but the main application entry point (`main.py`) still uses the hard-coded `SmaCross` strategy. To make the engine useful, it must be integrated into the core backtesting workflow.
*   **Items to implement:**
    *   Modify `src/main.py` to use the `StrategyEngine`.
    *   Create a sample `StrategyDefinition` object in `main.py` that represents a simple strategy (e.g., EMA Crossover).
    *   Pass this definition to the `StrategyEngine` to generate a dynamic strategy class.
    *   Pass the dynamically generated strategy to the `Backtester` service.
*   **Tests to cover:**
    *   Update `tests/test_main.py` (if it exists) or manually verify that the end-to-end flow in `main.py` runs successfully with the dynamic strategy.
*   **Acceptance Criteria (AC):**
    *   Running `python src/main.py` executes a backtest using a strategy dynamically generated by the `StrategyEngine`.
*   **Definition of Done (DoD):**
    *   `main.py` is updated to use the `StrategyEngine`, demonstrating a complete, albeit simple, dynamic workflow.
*   **Time estimate:** 1 hour
*   **Status:** Completed

---

## Epic 4: Maintenance & Refinement

*Goal: To address bugs, dependency issues, and minor refactorings that improve the overall health and stability of the codebase.*

---

### Task 5.2 — Environment and Dependency Fixes

*   **Rationale:** During the implementation of Task 5.1, several critical dependency and environment issues were discovered that prevented the application from running. These were documented in `docs/memory.md` and fixed to ensure the project is runnable.
*   **Items to implement:**
    *   Installed `setuptools` to resolve `pkg_resources` dependency for `pandas-ta`.
    *   Downgraded `numpy` to `<2.0` to resolve `numpy.NaN` import error in `pandas-ta`.
    *   Installed `pyarrow` to enable pandas Parquet caching functionality.
    *   Fixed an incorrect argument in the `DataService.get_data` call in `main.py`.
    *   Exposed `StrategyEngine` in `src/services/__init__.py` to allow correct imports.
*   **Acceptance Criteria (AC):**
    *   The `src/main.py` script can run end-to-end without import or dependency errors.
*   **Definition of Done (DoD):**
    *   All dependency issues are resolved and the fixes are committed.
*   **Time estimate:** 1.5 hours
*   **Status:** Completed

---

### Task 6 — Implement LLM Service & Prompt Management

*   **Rationale:** To create a dedicated, mockable service for all LLM API interactions, managing API keys securely and constructing the precise prompts that guide the AI's suggestions.
*   **Items to implement:**
    *   Add the client library for the chosen LLM provider (e.g., `openai` or `openrouter-client`) to `requirements.txt`.
    *   Create `services/llm_service.py`.
    *   Implement an `LLMService` class with a method `get_suggestion(history: list[PerformanceReport])` that:
        *   Loads the LLM provider and API key from environment variables (H-15).
        *   Loads a base prompt from `prompts/quant_analyst.txt`.
        *   Formats the `history` of reports into a string for context.
        *   Constructs the final prompt and sends it to the configured LLM API (e.g., OpenRouter with model `moonshotai/kimi-k2:free`) (mark `# impure`).
        *   Logs token counts for the request and response (H-22, H-23).
        *   Includes retry logic for transient API errors.
        *   Returns the raw JSON string from the LLM response.
    *   Create the initial `prompts/quant_analyst.txt` file.
*   **Tests to cover:**
    *   Create `tests/test_llm_service.py`.
    *   Mock the LLM API client and verify the service constructs the correct prompt string from a sample history.
*   **Acceptance Criteria (AC):**
    *   The service can send a well-formatted prompt to the LLM API.
    *   API keys are handled securely.
    *   Token usage is logged.
*   **Definition of Done (DoD):**
    *   `llm_service.py`, the prompt file, and tests are implemented and committed.
*   **Time estimate:** 2.5 hours
*   **Status:** Completed

---

### Task 7 — Implement State Manager for Resumability

*   **Rationale:** To make the system robust against interruptions. The state manager ensures that a long run can be resumed from the last successfully completed iteration, saving time and API costs.
*   **Items to implement:**
    *   Create `core/models.py` with a `RunState` model to hold `iteration_number` and `history`.
    *   Create `services/state_manager.py`.
    *   Implement a `StateManager` class with `save_state` and `load_state` methods.
    *   `save_state` writes the `RunState` to `run_state.json` atomically (using a temp file and rename).
    *   `load_state` reads the `RunState` from `run_state.json`, returning a default state if the file doesn't exist or is corrupt.
*   **Tests to cover:**
    *   Create `tests/test_state_manager.py` to test:
        *   Saving and loading a valid `RunState`.
        *   Loading a non-existent state file.
        *   Loading a corrupted or invalid state file.
*   **Acceptance Criteria (AC):**
    *   The run state is persisted to disk atomically.
    *   The system can be prepared to resume a run from a previously saved state.
*   **Definition of Done (DoD):**
    *   `state_manager.py` and its tests are implemented and committed.
    *   All related code passes `mypy --strict`.
*   **Time estimate:** 2 hours
*   **Status:** Completed

---

### Task 8 — Implement the Core Orchestrator Loop

*   **Rationale:** To tie all components together into the main automated feedback loop, orchestrating the flow from backtesting to LLM suggestion to the next iteration, including state management and pruning logic.
*   **Items to implement:**
    *   Create `core/orchestrator.py`.
    *   Implement the main `Orchestrator` class, injecting all required services in its `__init__` (H-2).
    *   Implement the `run()` method that:
        1.  Uses the `StateManager` to load the `RunState` for the current ticker, resuming from the last completed iteration if state exists.
        2.  Loops for the configured number of iterations.
        3.  Inside the loop: runs backtest, generates a `PerformanceReport`, appends it to the `RunState` history, and uses the `StateManager` to save the updated `RunState` to disk.
        4.  Implements the pruning mechanism (FR6).
        5.  Calls `LLMService` to get the next strategy suggestion.
        6.  Handles JSON parsing errors from the LLM gracefully (H-25).
*   **Tests to cover:**
    *   Create `tests/test_orchestrator.py`.
    *   This is an integration test. Mock all services (`LLMService`, `Backtester`, etc.).
    *   Provide a predictable sequence of mock LLM responses and assert that the orchestrator completes the loop, calls services in the correct order, and handles a "pruned" iteration correctly.
*   **Acceptance Criteria (AC):**
    *   The system can run a multi-iteration loop automatically.
    *   State is loaded at the start and saved after each iteration.
    *   The pruning logic correctly discards failed strategies.
*   **Definition of Done (DoD):**
    *   `orchestrator.py` and its integration test are implemented and committed.
*   **Time estimate:** 4 hours
*   **Status:** Completed

---

### Task 9 — Enhance Prompt Engineering with Explicit Failure Signaling

*   **Rationale:** To improve the integrity of the learning signal by explicitly informing the LLM when its suggestions fail, providing crucial negative feedback that is currently missing from the loop.
*   **Items to implement:**
    *   In `services/llm_service.py`, modify the `get_suggestion` method to accept an optional "failure context" argument.
    *   In `core/orchestrator.py`, when a strategy is "pruned", it must pass the failed strategy's JSON and its poor performance metrics as the "failure context" to the `LLMService`.
    *   The `LLMService` will then prepend a clear, explicit message to the next prompt, such as:
        > **"CRITICAL FEEDBACK: Your previous suggestion (Strategy JSON: {...}) was a failure. It was tested and resulted in a Sharpe Ratio of -0.5, which is below the required threshold. This result has been discarded. We are reverting to the previous best strategy. Analyze the failure and propose a substantially different approach."**
*   **Tests to cover:**
    *   Update `tests/test_llm_service.py` to verify that when a failure context is provided, this specific warning message is included in the prompt sent to the mock LLM client.
*   **Acceptance Criteria (AC):**
    *   The LLM is explicitly notified of pruned iterations and the reason for the failure, improving the learning signal.
*   **Definition of Done (DoD):**
    *   The prompt generation logic is updated to include explicit negative feedback.
*   **Time estimate:** 1.5 hours
*   **Status:** Not Started

---

## Epic 3: Finalization & Operational Polish

*Goal: To wrap the system in a user-friendly CLI, implement the crucial final validation step, and generate the comprehensive, human-readable reports that are the ultimate output of the tool.*

---

### Task 10 — Implement Final Validation & Reporting

*   **Rationale:** To combat overfitting by running the best-found strategy on unseen data and to generate the final, auditable artifacts that summarize the entire discovery process.
*   **Items to implement:**
    *   In `core/orchestrator.py`, add logic to run *after* the main loop completes.
    *   This logic must:
        1.  Identify the single best strategy from the history based on its Sharpe Ratio on the **training data** (H-24).
        2.  Run this single best strategy on the unseen **validation set** (H-19).
        3.  Generate a separate performance report for this validation run.
        4.  Create the final output directory structure as specified in the PRD (FR7).
        5.  Generate the `summary_report.md` with the comparison table.
        6.  Save the `full_run_log.json`.
        7.  Save the `backtesting.py` HTML plots for the best strategy on both train and validation data.
*   **Tests to cover:**
    *   Update `tests/test_orchestrator.py` to assert that the final validation methods are called with the correct (validation) data after the loop.
*   **Acceptance Criteria (AC):**
    *   The validation dataset is touched only once, after all iterations are complete.
    *   The final `summary_report.md` and all other artifacts are generated correctly in a timestamped directory.
*   **Definition of Done (DoD):**
    *   The final validation and report generation logic are implemented and committed.
*   **Time estimate:** 3 hours
*   **Status:** Not Started

---

### Task 11 — Implement CLI, Logging, and Final Output

*   **Rationale:** To create the primary user interface for the tool, providing clear feedback during a run and presenting the final results in a human-readable format.
*   **Items to implement:**
    *   In `main.py`, use `argparse` or `click` to create the final CLI.
    *   Set up a centralized logger (e.g., in `utils/logging_config.py`) that is configured once in `main.py` (H-10).
    *   Throughout the application (Orchestrator, services), replace all `print()` statements with calls to the logger at appropriate levels (INFO, DEBUG, ERROR).
    *   Ensure the console provides clear, real-time status updates (e.g., "TICKER: Running Iteration 3/10...", "Awaiting LLM response...").
    *   The `main.py` script should instantiate all services and the `Orchestrator`, then call `orchestrator.run()`.
*   **Tests to cover:**
    *   N/A for direct CLI testing, but manual end-to-end testing is required.
*   **Acceptance Criteria (AC):**
    *   The application is started via `python main.py`.
    *   The console provides useful, real-time status updates.
    *   No `print()` statements exist outside of `main.py`.
*   **Definition of Done (DoD):**
    *   The CLI and logging are fully implemented, and a full run can be initiated and monitored from the command line.
*   **Time estimate:** 2 hours
*   **Status:** Not Started

---

### Task 12 — Fix Critical Bugs and Improve Robustness

*   **Rationale:** To address critical bugs discovered during runs that caused crashes and prevented the system from completing its optimization loop. This task enhances the engine's stability and correctness.
*   **Items to implement:**
    *   **Fix `FileExistsError` in `StateManager`:** Replaced `pathlib.Path.rename()` with `os.replace()` to ensure atomic, cross-platform state saving.
    *   **Fix `NameError` for `adx` in `StrategyEngine`:** Added specific handling for the `adx` indicator to correctly map its multi-column output to predictable variable names, preventing crashes when the LLM suggests using it.
    *   **Documented fixes in `docs/memory.md`:** Added entries for the `FileExistsError` and `NameError` to prevent future regressions.
*   **Tests to cover:**
    *   Created `tests/test_strategy_engine_adx.py` to provide specific test coverage for the `adx` indicator fix and prevent regressions.
*   **Acceptance Criteria (AC):**
    *   The application no longer crashes due to `FileExistsError` on Windows.
    *   The `StrategyEngine` can successfully process strategies involving the `adx` indicator.
    *   The new test passes, and all existing tests continue to pass.
*   **Definition of Done (DoD):**
    *   The bug fixes are implemented, documented, and covered by tests.
*   **Time estimate:** 2 hours
*   **Status:** Completed