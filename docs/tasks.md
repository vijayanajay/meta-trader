Of course. Here is a comprehensive and detailed task breakdown for implementing the "Praxis" engine, written with the specified mindset of Kailash Nadh and ensuring no detail from the PRD, project brief, or architecture is missed.

---

# **"Praxis" Engine — Task Breakdown**

This document provides a detailed, sequential list of tasks required to build the "Praxis" Mean-Reversion Engine. Each task is designed as a small, logical unit of work, mapping directly to the requirements in the `prd.md` and `architecture.md`. We build methodically, test rigorously, and earn complexity. We do not build for a hypothetical future.

## Epic 1: Bedrock - The Data & Statistical Foundation

*Goal: To establish a reliable, reproducible data pipeline and the core statistical tools. Without a rock-solid foundation of clean, correct data and validated mathematical functions, the entire system is worthless. This epic builds the non-negotiable prerequisites.*

---

### Task 1 — Project Scaffolding & Configuration

*   **Rationale:** A project's long-term viability is decided in the first hour. We will establish a clean, reproducible structure and a centralized, type-safe configuration system from the outset. No shortcuts.
*   **Items to implement:**
    *   Create the full directory structure as defined in `architecture.md` (`praxis_engine/`, `core/`, `services/`, `prompts/`, etc.).
    *   Initialize a Git repository with a `.gitignore` that excludes `data_cache/`, `results/`, `__pycache__/`, and `.env`.
    *   Create `pyproject.toml` to define the project and configure `mypy` for strict type checking.
    *   Create `config.ini` with sections for `[data]`, `[strategy_params]`, `[filters]`, and `[llm]`. Populate with all thresholds from the PRD (e.g., `sector_vol_threshold = 22.0`, `liquidity_turnover_crores = 5.0`).
    *   Implement `services/config_service.py` to load and parse `config.ini`.
    *   Implement `core/models.py` with a Pydantic `Config` model that provides type-safe access to all configuration values.
    *   Create the CLI entry point `main.py` using `Typer` with a placeholder command that loads the config and prints it.
*   **Status:** Complete

---
### Task 1.1 — Fix Typer CLI Invocation

*   **Rationale:** The Typer CLI is not working as expected. This needs to be fixed to ensure the CLI is usable.
*   **Items to implement:**
    *   Investigate the `Typer` invocation issue mentioned in `docs/memory.md`.
    *   Fix the issue and ensure that `python -m praxis_engine.main verify-config` works as expected.
*   **Status:** Complete. **Resolution**: The CLI invocation was fixed by establishing a robust poetry script entry point (`poetry run praxis`) and moving all business logic out of `praxis_engine/__init__.py` into a dedicated `cli.py` module. The `run.py` script was deprecated in favor of this standard mechanism and has now been deleted from the repository.

---

### Task 1.2 — Solidify Project Dependencies
*   **Rationale:** The project is missing a formal dependency management file (e.g., `requirements.txt`). Several libraries (`typer`, `pyarrow`, `openai`, etc.) were required to run the backtest but were not installed as part of the initial setup, causing runtime errors. This makes the project difficult to set up and violates the principle of a reproducible environment.
*   **Items to implement:**
    1.  Create a `requirements.txt` file that lists all necessary dependencies for running the application and the tests.
    2.  Update the `README.md` or a new `CONTRIBUTING.md` with clear instructions on how to set up the development environment using `pip install -r requirements.txt`.
    3.  Ensure all required packages are included so that a fresh checkout can be run with a single installation command.
*   **Status:** Done. **Resolution**: A `requirements.txt` file has been created at the project root, establishing a single source of truth for all runtime and development dependencies. This resolves the dependency management issues noted in `docs/memory.md`. The project can now be set up with a single command (`pip install -r requirements.txt`).

---

### Task 2 — Data Service for Indian Markets

*   **Rationale:** Data is the lifeblood. This service must be robust, efficient, and acutely aware of Indian market specifics. We will use the correct data sources and implement caching to make research fast and reproducible.
*   **Items to implement:**
    *   Add `yfinance` and `pyarrow` to `pyproject.toml`.
    *   Implement `services/data_service.py` with a `DataService` class.
    *   The `get_data(stock, start_date, end_date)` method must:
        1.  Construct a cache filename (e.g., `HDFCBANK_2010-01-01_2023-12-31.parquet`).
        2.  If the cache file exists, load and return the DataFrame from it.
        3.  If not, fetch equity data using `yfinance.download`.
        4.  Fetch the corresponding Nifty sector index data using `yfinance`.
        5.  Calculate the 20-day rolling annualized `sector_vol` and merge it into the main DataFrame.
        6.  Perform basic cleaning and save the final, clean DataFrame to the Parquet cache file.
*   **Status:** Complete

---

### Task 3 — Core Statistical & Indicator Library

*   **Rationale:** To create a library of pure, well-tested functions for all required statistical tests and technical indicators. These are the mathematical building blocks of our strategy and must be provably correct.
*   **Items to implement:**
    *   Create `core/indicators.py` for technical indicators. Implement functions for:
        *   Bollinger Bands (`bbands(series, length, std)`)
        *   Relative Strength Index (`rsi(series, length)`)
    *   Create `core/statistics.py` for statistical tests. Implement functions for:
        *   Augmented Dickey-Fuller test (`adf_test(series)`) which returns the p-value.
        *   Hurst Exponent (`hurst_exponent(series)`) which returns the H value.
*   **Status:** Complete

---

## Epic 2: The Filtering Cascade - Signal & Validation

*Goal: To codify the core logic of the system. This involves translating the multi-frame signal generation rules and the non-negotiable statistical and contextual guardrails into deterministic code. This is where the "edge" is built.*

---

### Task 4 — Multi-Frame Signal Engine

*   **Rationale:** A simple BB+RSI signal is noise. The PRD specifies that the edge comes from multi-frame alignment. This engine will implement that precise logic to generate preliminary signals.
*   **Items to implement:**
    *   In `core/models.py`, define a Pydantic `Signal` model to hold entry price, stop-loss, and other relevant signal data.
    *   Implement `services/signal_engine.py` with a `SignalEngine` class.
    *   The `generate_signal(df_daily)` method must implement the exact multi-frame alignment check from the PRD.
    *   If the condition is met, populate and return a `Signal` object. Otherwise, return `None`.
*   **Status:** Complete

---

### Task 5 — The Guardrail Gauntlet: Validation Service

*   **Rationale:** This is the most critical part of the system. A preliminary signal means nothing until it has survived our gauntlet of statistical and contextual checks. This service acts as the primary capital preservation mechanism.
*   **Items to implement:**
    *   Implement `services/validation_service.py` with a `ValidationService` class.
    *   Create private helper methods for each "guard" (`liquidity`, `market_regime`, `statistical_validity`).
    *   Implement a public `validate(df)` method that calls these checks sequentially.
*   **Status:** Complete. **Resolution**: The initial monolithic service was refactored into modular `Guard` classes as specified in the architecture document, improving maintainability.

---

## Epic 3: The Grinder - Realistic Backtesting

*Goal: To build a brutally realistic, cost-aware backtesting framework. The purpose of a backtest is not to produce a beautiful equity curve, but to see if a strategy can survive real-world frictions. Gross returns are a fantasy.*

---

### Task 6 — Execution Simulator with Indian Cost Model

*   **Rationale:** A trade is not just an entry and an exit; it's a series of transactions that incur costs. This component will simulate a single trade with a painfully realistic model of Indian market costs.
*   **Items to implement:**
    *   In `core/models.py`, define a `Trade` model.
    *   Implement `services/execution_simulator.py` with an `ExecutionSimulator` class.
    *   Implement a `simulate_trade` method that applies the full cost model (brokerage, STT, slippage).
*   **Status:** Complete. **Resolution**: The cost model was corrected to use the tiered slippage model from the architecture document. Logic was also added to handle zero-volume scenarios gracefully.

---

### Task 7 — Walk-Forward Backtesting Orchestrator

*   **Rationale:** To tie all the components together into a scientifically valid backtesting loop. We use a walk-forward approach to mitigate lookahead bias and simulate how the strategy would have performed in real time.
*   **Items to implement:**
    *   Implement `core/orchestrator.py` with an `Orchestrator` class.
    *   Implement the `run_backtest(stock)` method that correctly implements the walk-forward loop.
    *   Integrate all services (`DataService`, `SignalEngine`, `ValidationService`, `ExecutionSimulator`, `LLMAuditService`).
*   **Status:** Complete. **Resolution**: Critical data leakage issues were fixed, and the orchestrator was updated to efficiently calculate historical performance for the LLM audit service.

---

## Epic 4: The Auditor & The Output

*Goal: To integrate the LLM as a final statistical auditor and to produce the clear, actionable reports that are the system's final output.*

---

### Task 8 — LLM Audit Service with OpenRouter

*   **Rationale:** To integrate the LLM in its narrowly defined role: a statistical auditor. This service will be responsible for all communication with the LLM, strictly enforcing the "no price data" rule.
*   **Items to implement:**
    *   Implement `services/llm_audit_service.py` with an `LLMAuditService` class.
    *   The `get_confidence_score` method must query the LLM with a statistics-only prompt.
    *   It must robustly parse the LLM's response.
*   **Status:** Complete. **Resolution**: A critical performance issue was resolved by removing the "mini-backtest" logic from this service. The service is now a lean, stateless utility that relies on the Orchestrator to provide historical context, as per the architecture. The service was further hardened to handle multiple LLM providers (`OpenAI`, `OpenRouter`) controlled via environment variables. Test coverage was increased to >90% to cover initialization failures, API errors, and other edge cases. The default behavior for unconfigured providers was changed to be fail-safe (return 0.0 score).

---

### Task 9 & 11 — Final Report Generation & CLI

*   **Rationale:** To synthesize the results and expose the system's functionality through a clean command-line interface.
*   **Items to implement:**
    *   Implement `services/report_generator.py`.
    *   Implement `generate_backtest_report` and `generate_opportunities_report` methods.
    *   Expand the Typer CLI in `main.py` with `backtest` and `generate-report` commands.
*   **Status:** Complete. **Resolution**: The `generate-report` command was previously incorrect and inefficient. It has been refactored to be correct and consistent with the backtesting logic. The CLI is now robustly accessible via a poetry script entry point.


### Task 11 — Implement Dynamic, Volatility-Based Exits

*   **Rationale:** The current fixed 20-day exit is a blunt, arbitrary instrument. It's a magic number that ignores the single most important variable after a trade is entered: volatility. A strategy cannot be considered robust if its exit logic is static while the market is dynamic. This task replaces the fixed exit with a data-driven one based on the stock's own recent volatility (ATR), making our risk management adaptive and provably linked to market conditions. This directly addresses a key future enhancement noted in the PRD.
*   **Items to implement:**
    1.  In `core/indicators.py`, add a new function `atr(high_series, low_series, close_series, length)` to calculate the Average True Range.
    2.  In `config.ini`, add a new `[exit_logic]` section. Include parameters like `use_atr_exit = True`, `atr_period = 14`, `atr_stop_loss_multiplier = 2.5`, and `max_holding_days = 40`.
    3.  In `core/models.py`, add a corresponding `ExitLogicConfig` Pydantic model and integrate it into the main `Config` model.
    4.  Modify the `Orchestrator.run_backtest` loop. The current logic that determines the exit (`exit_date_target_index = i + signal.exit_target_days`) must be replaced.
    5.  After a trade is initiated at index `i`, the orchestrator must now loop forward day-by-day (up to `max_holding_days`).
    6.  In this new inner loop, it will calculate the ATR-based trailing stop-loss for each day. The exit is triggered on the first day the low price breaches the stop-loss.
    7.  The orchestrator will pass the determined `exit_date_actual` and `exit_price` to the `ExecutionSimulator`, whose interface will not need to change, thus preserving architectural boundaries.
*   **Tests to cover:**
    *   Add a test to `tests/test_indicators.py` for the new `atr` function, validating its output against a known result.
    *   In `tests/test_orchestrator.py`, create a new integration test with a synthetic DataFrame where the price clearly hits a pre-calculated ATR stop-loss. Assert that the trade exits on the correct day and at the correct price.
    *   Create another test where the price meanders and never hits the stop-loss. Assert that it exits on the `max_holding_days` timeout.
*   **Acceptance Criteria (AC):**
    *   The backtester can be configured via `config.ini` to use either the legacy fixed-day exit or the new ATR-based exit.
    *   When the ATR exit is enabled, trades correctly exit based on hitting the trailing stop-loss or the max holding period.
*   **Definition of Done (DoD):**
    *   All new code is implemented, unit-tested, and integrated into the orchestrator. The `config.ini` is updated with the new section and documentation.
*   **Time estimate:** 6 hours
*   **Status:** Done

---

## Epic 5: Critical Refactoring & Validation

*Goal: To correct severe architectural flaws, data leakage, and inefficiencies discovered during a full-code review. These fixes are non-negotiable for the system to produce scientifically valid results.*

### Task 12 — Fix Lookahead Bias and Orchestrator Logic

*   **Rationale:** A full code review uncovered critical flaws that invalidated backtest results. The `Orchestrator` contained lookahead bias in its ATR calculation and had a catastrophically inefficient `generate_opportunities` method. This task corrects these core architectural problems to restore experimental integrity.
*   **Items to implement:**
    1.  **Fix ATR Lookahead Bias:** Move the ATR calculation from a pre-computation step on the full dataset to *inside* the `run_backtest` walk-forward loop. The ATR must be calculated only on the point-in-time `window` dataframe at each step.
    2.  **Refactor `generate_opportunities`:** The existing method, which ran a full backtest for every stock, was deleted. It has been replaced with a new, efficient implementation that:
        a. Checks for a signal and validates it only on the most recent data point.
        b. If the signal is valid, it calls a new helper method (`_calculate_historical_stats_for_llm`) to perform a lean, focused backtest on the data *prior* to the signal date.
        c. This provides the necessary historical context to the LLM without re-running the main backtester.
*   **Status:** Done


### Task 13 — Implement Systematic Parameter Sensitivity Analysis

*   **Rationale:** Blindly changing parameters in `config.ini` to find a better result is unscientific, inefficient, and prone to overfitting. This task introduces a systematic, reproducible framework to explore the parameter space. It transforms parameter tuning from guesswork into a controlled experiment, providing the data needed to make informed decisions about the system's risk/reward profile. This is fundamental to understanding the model's behavior and the true drivers of its performance (or lack thereof).
*   **Items to implement:**
    1.  In `config.ini`, add a new `[sensitivity_analysis]` section. This section will define the parameter to vary (e.g., `parameter_to_vary = "filters.sector_vol_threshold"`), a start value, an end value, and a step size.
    2.  In `run.py` and `praxis_engine/main.py`, add a new CLI command: `sensitivity-analysis`.
    3.  Create a new method in `core/orchestrator.py` called `run_sensitivity_analysis()`. This method will:
        a. Read the analysis parameters from the config.
        b. Loop through the specified range of values for the target parameter.
        c. In each iteration, create a *deep copy* of the main `Config` object and dynamically update the single parameter being tested. This is critical to ensure runs are isolated and the base configuration remains immutable.
        d. Run the full backtest across all configured stocks using this temporary, modified config.
        e. Store the aggregated KPIs (Sharpe, Profit Factor, Total Trades, etc.) for each parameter value.
    4.  In `services/report_generator.py`, add a new method `generate_sensitivity_report()`. This method will take the results from the analysis and format them into a clear Markdown table showing how performance metrics change as the parameter changes.
    5.  The `sensitivity-analysis` command will call the orchestrator and then the report generator, saving the final output to `results/sensitivity_analysis_report.md`.
*   **Tests to cover:**
    *   This is a high-level integration test. In a new `tests/test_orchestrator_analysis.py`, mock the `run_backtest` method.
    *   Call `run_sensitivity_analysis` and assert that `run_backtest` is called the correct number of times, corresponding to the steps in the parameter range.
    *   Crucially, assert that the `Config` object passed to the services during each mocked run contains the correctly modified parameter value for that specific iteration.
    *   In `tests/test_report_generator.py`, add a test for `generate_sensitivity_report` to verify the correct formatting of the output table.
*   **Acceptance Criteria (AC):**
    *   A new CLI command `praxis sensitivity-analysis` is available.
    *   Running the command executes multiple backtests as defined in the `[sensitivity_analysis]` section of `config.ini`.
    *   A Markdown report is generated in the `results/` directory that clearly tabulates the system's performance KPIs against each tested parameter value.
*   **Definition of Done (DoD):**
    *   All new code for the CLI, orchestrator, and report generator is implemented, unit-tested, and documented. The `config.ini` is updated with a documented example of the new section.
*   **Time estimate:** 8 hours
*   **Status:** Done

Understood. Task 14 is complete. Here are the updated `tasks.md` entries for the remaining work in Option 1, renumbered accordingly.

---

## Epic 6: Transition to Probabilistic Filtering

*Goal: To evolve the system from a rigid, binary filtering cascade into a more nuanced, probabilistic model. This involves refactoring the guards to produce continuous scores instead of true/false verdicts and empowering the LLM to weigh these scores as part of its final audit. This directly addresses the core issue of hyper-selectivity by allowing the system to evaluate signals on a spectrum of quality rather than a simple pass/fail basis.*

---

### Task 14 — Refactor Guards from Binary to Probabilistic Scoring

*   **Rationale:** The current `True/False` validation from the guards is a primary cause of the low trade count. A signal where the Hurst exponent is `0.451` is discarded as readily as one where it is `0.80`. This throws away valuable information. Refactoring the guards to return a continuous score (0.0 to 1.0) will allow the system to understand nuance—that a signal can be "weak but acceptable" in one dimension if it is "excellent" in others.
*   **Items to implement:**
    1.  **Models:** In `core/models.py`, create a new Pydantic model `ValidationScores(BaseModel)` with fields: `liquidity_score: float`, `regime_score: float`, `stat_score: float`. The existing `ValidationResult` model will be deprecated and removed.
    2.  **Guard Interface:** The `GuardProtocol` in `services/validation_service.py` must be updated. The `validate` method will now return a single `float` score.
    3.  **Guard Implementations:** Each guard's `validate` method must be rewritten to return a score instead of a `ValidationResult`.
        *   `LiquidityGuard`: Implement a linear scoring function. A turnover of `0.5 * threshold` might score `0.0`, while `2.0 * threshold` scores `1.0`.
        *   `RegimeGuard`: Implement a linear scoring function for sector volatility. A vol of `25%` might score `0.0`, while `10%` scores `1.0`.
        *   `StatGuard`: Calculate separate scores for the ADF p-value and the Hurst exponent, then return the geometric mean of the two scores.
    4.  **Validation Service:** The `ValidationService.validate` method must be completely refactored. It will no longer short-circuit. It must:
        a. Call every guard in its list.
        b. Collect the score from each guard.
        c. Return a populated `ValidationScores` object.
    5.  **Configuration:** Add new parameters to `config.ini` under a `[scoring]` section to control the boundaries of these new linear scoring functions (e.g., `hurst_score_min = 0.55`, `hurst_score_max = 0.3`).
*   **Tests to cover:**
    *   Update all tests in `tests/test_validation_service.py` to reflect the new return types and logic.
    *   Add specific tests for each guard's scoring function. For example, create a test for `StatGuard` with a known Hurst value and assert that the returned score is mathematically correct based on the configured boundaries.
*   **Acceptance Criteria (AC):**
    *   All guards return a float score between 0.0 and 1.0.
    *   The `ValidationService` successfully aggregates these scores into a `ValidationScores` object.
*   **Definition of Done (DoD):**
    *   All code is refactored, all new configuration is added, and all associated unit tests are updated and passing.
*   **Time estimate:** 8 hours
*   **Status:** Done

---

### Task 15 — Empower LLM with Guard Scores for Nuanced Auditing

*   **Rationale:** With the guards now producing rich, probabilistic data, the final step is to feed this information to the LLM. This completes the architectural vision of the LLM as a sophisticated, non-linear function that weighs multiple, continuous inputs to make a final judgment, moving it beyond the limitations of the original, statistics-only prompt.
*   **Items to implement:**
    1.  **Prompt Engineering:** Modify the `praxis_engine/prompts/statistical_auditor.txt` template. Add a new section for the guard scores, clearly labeling each one (e.g., `- Current Signal Quality - Liquidity Score: {{ liquidity_score }}`, `- Regime Score: {{ regime_score }}`, `- Statistical Score: {{ stat_score }}`).
    2.  **LLM Audit Service:** The `get_confidence_score` method in `services/llm_audit_service.py` must be updated. Its signature will now accept the `ValidationScores` object as an argument. The context dictionary passed to the Jinja2 template must be updated to include these new scores.
    3.  **Orchestrator Integration:** In `core/orchestrator.py`, update the main backtest loop. The call to `validation_service.validate()` will now return a `ValidationScores` object. This object must be passed directly to the subsequent call to `llm_audit_service.get_confidence_score()`.
    4.  **Orchestrator Pre-filter:** Add a simple pre-filter in the `Orchestrator` after the validation step. If the product of the scores (`liquidity * regime * stat`) is below a new, very low threshold in `config.ini` (e.g., `min_composite_score_for_llm = 0.05`), skip the LLM call to save resources on obviously terrible signals.
*   **Tests to cover:**
    *   In `tests/test_llm_audit_service.py`, update the `get_confidence_score` test. It should now pass a mock `ValidationScores` object. The core assertion will be to check that the rendered prompt string correctly includes the formatted scores.
    *   Update the integration tests in `tests/test_orchestrator.py` to mock the new return value from the `ValidationService` and assert that it is passed correctly to the `LLMAuditService`.
*   **Acceptance Criteria (AC):**
    *   The backtest log shows the new, expanded LLM prompt containing the guard scores.
    *   The system completes a full backtest run using the new end-to-end data flow.
*   **Definition of Done (DoD):**
    *   All code changes are implemented, the prompt is updated, and all relevant unit and integration tests are passing.
*   **Time estimate:** 4 hours
*   **Status:** Done

---

### Task 16 — Enhance Backtest User Experience

*   **Rationale:** The backtest output is verbose and hard to follow. A progress bar and per-stock summaries will make the backtesting process more user-friendly and provide immediate feedback on the performance of the strategy for each stock. The detailed logs will be moved to a file for later analysis.
*   **Items to implement:**
    1.  **File Logging:** Configure the logger to write detailed `DEBUG` level logs to `results/backtest_results.log`. The console logger should only show `INFO` level messages.
    2.  **Progress Bar:** Use `tqdm` to display a progress bar for the backtesting loop over the stocks.
    3.  **Per-Stock Summary:** After each stock is backtested, generate and print a summary of the results to the console.
    4.  **Less Verbose Orchestrator:** Change verbose `log.info` statements in the `Orchestrator` to `log.debug` to keep the console output clean.
*   **Status:** Done

## Epic 7: From Output to Insight - Advanced Diagnostics & Reporting

*Goal: To transform the backtest output from a simple KPI summary into a comprehensive diagnostic tool. This is not about changing the core strategy logic, but about instrumenting it to provide the deep, analytical insights required to improve it scientifically. A backtest that only tells you the final P/L is a missed opportunity; a backtest that tells you *why* you achieved that P/L is the foundation for progress. We will make our system's thinking transparent and auditable.*

---

### Task 17 — Instrument Backtest Runs with Reproducibility Metadata

*   **Rationale:** A backtest is a scientific experiment. An experiment without documented initial conditions is unreproducible and therefore invalid. This task ensures that every report is stamped with the exact context in which it was generated, adhering to `[H-23]`.
*   **Items to implement:**
    1.  **Git Hash:** Create a utility function (e.g., in a new `praxis_engine/utils.py`) that uses the `subprocess` module to execute `git rev-parse --short HEAD` and retrieve the current commit hash. This function must handle cases where Git is not installed or it's not a Git repository.
    2.  **Orchestrator:** The `Orchestrator` must gather the run timestamp, the path to the config file, and the Git hash at the beginning of a run.
    3.  **Report Generator:** The `generate_backtest_report` method in `services/report_generator.py` must be updated to accept this metadata.
    4.  **Output:** Add a new "Run Configuration & Metadata" section to the top of `backtest_summary.md` that displays this information in a clean Markdown table.
*   **Tests to cover:**
    *   A unit test for the new Git hash utility function, mocking the `subprocess.run` call.
    *   Update `tests/test_report_generator.py` to check that the metadata section is correctly rendered in the output string.
*   **Status:** Done

---

### Task 18 — Implement Signal Attrition Funnel and Guardrail Rejection Tracking

*   **Rationale:** The system's primary function is to filter. We are blind to its effectiveness if we don't measure what it filters. This task instruments the entire decision-making pipeline to produce a "funnel," showing exactly how many signals are discarded at each stage and, crucially, *why*. This is the most direct way to identify which guardrail is doing the most work, per `[The Nadh Principle]` of pragmatic simplicity.
*   **Items to implement:**
    1.  **Orchestrator State:** Modify the `Orchestrator`'s main `backtest` loop in `praxis_engine/main.py`. It must now maintain counters for: `potential_signals`, `rejections_by_guard`, `rejections_by_llm`, and `trades_executed`. The `rejections_by_guard` should be a dictionary counting rejections per guard type (e.g., `{'StatGuard': 0, 'RegimeGuard': 0}`).
    2.  **Rejection Logic:** In `core/orchestrator.py`, after `validation_service.validate()` returns the `ValidationScores`, if the composite score is below the `min_composite_score_for_llm` threshold, determine the primary reason for rejection by finding which score (`liquidity`, `regime`, or `stat`) was the lowest. Increment the corresponding counter.
    3.  **Data Aggregation:** The main loop must aggregate these counts across all stocks.
    4.  **Report Generator:** Create new methods in `services/report_generator.py` to generate the "Filtering Funnel" and "Guardrail Rejection Analysis" tables from the aggregated counter data.
*   **Tests to cover:**
    *   In `tests/test_orchestrator.py`, create a new test that mocks the return values of the services to simulate a flow where signals are rejected by different guards. Assert that the final counts returned by the orchestrator are correct.
    *   In `tests/test_report_generator.py`, add tests for the new funnel and rejection table generation methods.
*   **Status:** Done
*   **Resolution:** The signal attrition funnel and rejection tracking have been fully implemented in the Orchestrator and Report Generator. The logic correctly tracks potential signals and their rejections at both the guardrail and LLM audit stages. Unit and integration tests have been added to verify this functionality. It was observed during testing that the current strategy configuration is highly restrictive and results in zero trades, which the system now correctly reports. The implementation is sound; tuning the strategy parameters is a separate task.

---

### Task 19 — Add Per-Stock Performance Breakdown

*   **Rationale:** System-wide averages are deceptive; they hide excellence and mediocrity. A strategy might be brilliant on 5 stocks and terrible on 20. This task provides the granular, per-stock data needed to understand where the strategy actually works, enabling intelligent pruning of the stock universe.
*   **Items to implement:**
    1.  **Orchestrator Return Value:** The `Orchestrator.run_backtest` method must be refactored. Instead of just returning a list of trades, it should return a dictionary or a data class containing the trades for that stock *and* the rejection counts for that stock.
    2.  **CLI Aggregation:** The `backtest` command in `praxis_engine/main.py` must be updated to handle this new return type. It will aggregate the per-stock results into a master data structure (e.g., a dictionary keyed by stock symbol).
    3.  **Report Generator:** Add a new method `generate_per_stock_report` to `services/report_generator.py`. This method will take the aggregated per-stock data and format it into the specified Markdown table, including trade counts, P/L, and rejection statistics for each stock.
*   **Tests to cover:**
    *   Update tests in `tests/test_orchestrator.py` to reflect the new return signature of `run_backtest`.
    *   Add a new test in `tests/test_report_generator.py` to verify the correct formatting of the per-stock table.
*   **Status:** To Do

---

### Task 20 — Implement Trade Distribution and Statistical Analysis

*   **Rationale:** To move beyond simple averages and understand the *character* of the strategy's returns, per the Hinton mindset. A strategy with a positive average return driven by one massive outlier is fundamentally different and riskier than one with consistent small gains. This task adds the statistical measures (skew, kurtosis) and visualizations needed to see the true shape of the P/L distribution.
*   **Items to implement:**
    1.  **Pandas Dependency:** Ensure `pandas` is used for statistical calculations to avoid adding new dependencies like `scipy`, adhering to `[H-8]`.
    2.  **Report Generator:** In `services/report_generator.py`, enhance the `_calculate_kpis` method (or create a new one) to compute:
        *   Average Win %, Average Loss %
        *   Best Trade %, Worst Trade %
        *   Average Holding Period in days.
        *   Skewness and Kurtosis of the net return series (`pd.Series(returns).skew()`, `.kurt()`).
    3.  **ASCII Histogram:** Create a new, pure utility function (e.g., in `praxis_engine/utils.py`) called `generate_ascii_histogram(data: List[float]) -> str`. This function will bin the returns and generate a simple text-based histogram.
    4.  **Output:** Integrate the new table and the histogram into the `backtest_summary.md` output.
*   **Tests to cover:**
    *   A unit test for the `generate_ascii_histogram` utility with a known data set to verify the output format.
    *   Update `tests/test_report_generator.py` to assert that the new distribution table and histogram are present and correctly formatted in the final report string.
*   **Status:** To Do

---

### Task 21 — Implement LLM Performance Uplift Analysis

*   **Rationale:** The LLM is the most expensive and opaque component of the system. Its value cannot be assumed; it must be rigorously quantified. This task implements a baseline comparison to measure the LLM's direct contribution (or harm) to the strategy's performance, adhering to Hinton's principle of isolating and measuring the impact of intelligent components (`[H-26]`).
*   **Items to implement:**
    1.  **Orchestrator Logic Change:** This is a critical refactoring of `core/orchestrator.py`.
        a. After a signal passes the guardrail pre-filter, the `Orchestrator` must immediately simulate the trade as if it were to be executed. This trade object is stored in a new list, `pre_llm_trades`.
        b. *Then*, the signal is sent to the `LLMAuditService`.
        c. If the LLM confidence score is sufficient, the *exact same trade object* is also appended to the final `trades` list.
        d. The `run_backtest` method must now return both lists: `pre_llm_trades` and `final_trades`.
    2.  **LLM Score Logging:** The `Orchestrator` must collect every confidence score returned by the `LLMAuditService` throughout the backtest into a list.
    3.  **Report Generator:** Create a new method `generate_llm_uplift_report`. It will:
        a. Accept the `pre_llm_trades` and `final_trades` lists.
        b. Calculate KPIs for both sets of trades.
        c. Compute the percentage uplift (or decline) for key metrics like Profit Factor and Win Rate.
        d. Use the `generate_ascii_histogram` utility to create a distribution chart of the collected LLM scores.
        e. Format all of this into the "LLM Audit Performance Analysis" section.
*   **Tests to cover:**
    *   This requires a significant update to `tests/test_orchestrator.py`. Create a new integration test that simulates a scenario where some signals pass the guards but are then rejected by the LLM. Assert that `run_backtest` returns two lists of trades with the correct contents.
    *   Add a new test to `tests/test_report_generator.py` for `generate_llm_uplift_report`, providing it with two mock lists of trades and asserting the final table and uplift calculations are correct.
*   **Status:** To Do

---

### Task 22 — Align Task Numbers with Descriptions
*   **Rationale:** There is a discrepancy between user requests for specific task numbers (e.g., "Task 17") and the content of those tasks in this document. This indicates that task numbering may be out of sync with the project owner's view.
*   **Items to implement:**
    *   Review all tasks and ensure their numbers and descriptions are consistent and up-to-date with the project owner's expectations.
    *   This is a documentation and project management task.
*   **Status:** To Do