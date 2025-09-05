# **"Praxis" Engine — Task Breakdown**

This document provides a detailed, sequential list of tasks required to build the "Praxis" Mean-Reversion Engine. Each task is designed as a small, logical unit of work, mapping directly to the requirements in the `prd.md` and `architecture.md`. We build methodically, test rigorously, and earn complexity. We do not build for a hypothetical future.

---

## Concise Summary (Kailash Nadh style) — Tasks 1–15

Below are short, pragmatic summaries for Tasks 1 through 15: rationale, what was implemented, the resolution, and the current status. The tone is direct and focused on engineering trade-offs and outcomes.

1) Task 1 — Project Scaffolding & Configuration
* Rationale: Start clean; configuration must be type-safe and reproducible.
* Implemented: Project layout, `.gitignore`, `pyproject.toml`, `config.ini`, `services/config_service.py`, `core/models.py`, and a `Typer` CLI stub.
* Resolution: Foundations in place; CLI loads config successfully.
* Status: Complete

2) Task 1.1 — Fix Typer CLI Invocation
* Rationale: CLI must be reliable for developer workflows.
* Implemented: Fixed Typer invocation so module call works (`python -m praxis_engine.main verify-config`).
* Resolution: CLI is now usable from module mode.
* Status: Complete

3) Task 1.2 — Solidify Project Dependencies
* Rationale: Reproducible environments are mandatory.
* Implemented: `requirements.txt` created and README updated with install instructions.
* Resolution: Single-step environment setup available.
* Status: Done

4) Task 2 — Data Service for Indian Markets
* Rationale: Reliable, cached, India-aware data is non-negotiable.
* Implemented: `DataService` with cache logic, sector index merge, rolling sector vol calculation, parquet caching.
* Resolution: Fast, reproducible data fetches with correct sector context.
* Status: Complete

5) Task 3 — Core Statistical & Indicator Library
* Rationale: Indicators must be pure and testable.
* Implemented: `bbands`, `rsi`, `adf_test`, `hurst_exponent` in `core` modules.
* Resolution: Mathematical primitives validated and tested.
* Status: Complete

6) Task 4 — Multi-Frame Signal Engine
* Rationale: Multi-timeframe alignment is the source of edge.
* Implemented: `Signal` model and `SignalEngine.generate_signal` implementing PRD rules.
* Resolution: Reliable signal generation per spec.
* Status: Complete

7) Task 5 — Validation Service (Guardrail Gauntlet)
* Rationale: Capital preservation via sequential statistical/contextual checks.
* Implemented: `ValidationService` refactored to modular Guard classes for liquidity, regime, and stats.
* Resolution: Guardrail logic modular and testable.
* Status: Complete

8) Task 6 — Execution Simulator with Indian Cost Model
* Rationale: Realistic costs make results credible.
* Implemented: `ExecutionSimulator` with brokerage, STT, slippage, and zero-volume handling.
* Resolution: Trade P/L reflects Indian market frictions.
* Status: Complete

9) Task 7 — Walk-Forward Backtesting Orchestrator
* Rationale: Walk-forward prevents lookahead and models real-time behavior.
* Implemented: `Orchestrator.run_backtest` integrating DataService, SignalEngine, ValidationService, ExecutionSimulator, and LLM hook.
* Resolution: Orchestrator fixed for data leakage and performance.
* Status: Complete

10) Task 8 — LLM Audit Service with OpenRouter
* Rationale: LLM is a constrained statistical auditor only.
* Implemented: `LLMAuditService` with provider abstraction, fail-safe defaults, and high test coverage.
* Resolution: Lean, stateless auditor; handles provider errors and returns safe defaults.
* Status: Complete

11) Task 9 — Final Report Generation & CLI
* Rationale: Reports and CLI expose outcomes clearly.
* Implemented: `report_generator` functions and expanded Typer CLI commands for backtest and report generation.
* Resolution: Correct, efficient report generation and usable CLI entry points.
* Status: Complete

12) Task 10 — Dynamic, Volatility-Based Exits (ATR)
* Rationale: Exits must adapt to market volatility, not a magic constant.
* Implemented: `atr` in `core/indicators.py`, `ExitLogicConfig`, `config.ini` updates, and orchestrator loop changed to ATR trailing-stop logic; tests added.
* Resolution: ATR-based exits operational and test-covered; configurable fallback to legacy exit preserved.
* Status: Done

13) Task 11 — Fix Lookahead Bias and Orchestrator Logic
* Rationale: Lookahead bias invalidates experiments; generate_opportunities was inefficient.
* Implemented: ATR moved to walk-forward window, `generate_opportunities` refactored to lightweight recent checks and a focused historical helper for LLM context.
* Resolution: Backtest integrity restored and runtime reduced.
* Status: Done

14) Task 12 — Systematic Parameter Sensitivity Analysis
* Rationale: Move tuning from guesswork to controlled experiments.
* Implemented: `[sensitivity_analysis]` config, `sensitivity-analysis` CLI, `Orchestrator.run_sensitivity_analysis`, and reporting for sensitivity results; tests added.
* Resolution: Reproducible parameter sweeps and Markdown report generation implemented.
* Status: Done

15) Task 13 — Refactor Guards to Probabilistic Scoring
* Rationale: Binary guards throw away signal nuance; scores enable graded decisions.
* Implemented: `ValidationScores` model, guards return 0.0–1.0 scores, `ValidationService` aggregates scores, config controls boundaries; tests updated.
* Resolution: Guards now produce continuous scores consumed downstream.
* Status: Done


## Epic 7: From Output to Insight - Advanced Diagnostics & Reporting

*Goal: To transform the backtest output from a simple KPI summary into a comprehensive diagnostic tool. This is not about changing the core strategy logic, but about instrumenting it to provide the deep, analytical insights required to improve it scientifically. A backtest that only tells you the final P/L is a missed opportunity; a backtest that tells you *why* you achieved that P/L is the foundation for progress. We will make our system's thinking transparent and auditable.*

---

### Task 16 — Instrument Backtest Runs with Reproducibility Metadata

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

### Task 17 — Implement Signal Attrition Funnel and Guardrail Rejection Tracking

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

### Task 18 — Add Per-Stock Performance Breakdown

*   **Rationale:** System-wide averages are deceptive; they hide excellence and mediocrity. A strategy might be brilliant on 5 stocks and terrible on 20. This task provides the granular, per-stock data needed to understand where the strategy actually works, enabling intelligent pruning of the stock universe.
*   **Items to implement:**
    1.  **Orchestrator Return Value:** The `Orchestrator.run_backtest` method must be refactored. Instead of just returning a list of trades, it should return a dictionary or a data class containing the trades for that stock *and* the rejection counts for that stock.
    2.  **CLI Aggregation:** The `backtest` command in `praxis_engine/main.py` must be updated to handle this new return type. It will aggregate the per-stock results into a master data structure (e.g., a dictionary keyed by stock symbol).
    3.  **Report Generator:** Add a new method `generate_per_stock_report` to `services/report_generator.py`. This method will take the aggregated per-stock data and format it into the specified Markdown table, including trade counts, P/L, and rejection statistics for each stock.
*   **Tests to cover:**
    *   Update tests in `tests/test_orchestrator.py` to reflect the new return signature of `run_backtest`.
    *   Add a new test in `tests/test_report_generator.py` to verify the correct formatting of the per-stock table.
*   **Status:** Done

---

### Task 19 — Implement Trade Distribution and Statistical Analysis

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
*   **Status:** Done

---

### Task 20 — Implement LLM Performance Uplift Analysis

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
*   **Status:** Done

---
### Task 21 — Align Task Numbers with Descriptions
*   **Rationale:** There is a discrepancy between user requests for specific task numbers (e.g., "Task 17") and the content of those tasks in this document. This indicates that task numbering may be out of sync with the project owner's view.
*   **Items to implement:**
    *   Review all tasks and ensure their numbers and descriptions are consistent and up-to-date with the project owner's expectations.
    *   This is a documentation and project management task.
*   **Status:** Done


---

### Task 22 — Harden LLM API Connectivity

*   **Rationale:** The backtest runs are consistently failing with `APIConnectionError` when trying to reach the OpenRouter service. This prevents any signal from passing the LLM audit, effectively halting the strategy. The service needs to be made more resilient to these network-level issues.
*   **Items to implement:**
    1.  **Investigate Root Cause:** Determine if the `APIConnectionError` is due to an invalid API key, a problem with the OpenRouter service itself, or a local network configuration issue.
    2.  **Implement Exponential Backoff:** Wrap the `llm_audit_service`'s API call in a retry loop with exponential backoff (e.g., using the `tenacity` library or a manual implementation) to handle transient network errors more gracefully.
    3.  **Add Timeout:** Configure a reasonable timeout for the API request to prevent the system from hanging indefinitely.
    4.  **Improve Error Logging:** Enhance the logging in `LLMAuditService` to provide more context when an API error occurs, including the number of retries attempted.
*   **Tests to cover:**
    *   Add a test to `tests/test_llm_audit_service.py` that mocks the API client to throw an `APIConnectionError` and asserts that the retry logic is triggered the correct number of times.
*   **Status:** Done

---
### Task 23 — Update PRD and other documentation
*   **Rationale:** The PRD and other documentation may be out of date with the current implementation. This task is to review and update the documentation to reflect the current state of the project.
*   **Items to implement:**
    *   Review `docs/prd.md` and update it to reflect the use of OpenRouter and the Kimi 2 model.
    *   Review `docs/memory.md` and add any new learnings.
    *   Review `README.md` and update if necessary.
*   **Status:** To Do

---

### Task 24 — Implement Dynamic Profit Target for Symmetrical Risk Management

*   **Rationale:** (Hinton) The backtest report shows a negative skew of -0.94. This is a statistical warning that our profit distribution has a longer tail on the left; our losses, when they occur, are more severe than our wins are beneficial. This creates a poor risk-adjusted return profile. (Nadh) Architecturally, our exit logic is asymmetrical and incomplete. We have a well-defined rule for when we are wrong (the ATR stop-loss) but no rule for when we are right. We are letting profitable trades run indefinitely until a timeout, which is arbitrary. This task introduces a symmetrical, data-driven profit target to test the hypothesis that systematically capturing gains will improve the Sharpe Ratio by shaping a more favorable return distribution.
*   **Items to implement:**
    1.  **Configuration:** In `config.ini`, within the `[exit_logic]` section, add a new parameter: `reward_risk_ratio = 2.0`.
    2.  **Models:** In `core/models.py`, add the corresponding `reward_risk_ratio: float` field to the `ExitLogicConfig` Pydantic model.
    3.  **Orchestrator Logic:** Refactor the `Orchestrator._determine_exit` method in `core/orchestrator.py`.
        a. At the point of trade entry (at index `i`), calculate the risk distance: `risk_per_share = entry_price - stop_loss_price`.
        b. Calculate the profit target: `profit_target_price = entry_price + (risk_per_share * self.config.exit_logic.reward_risk_ratio)`.
        c. Inside the day-by-day forward loop that checks for the stop-loss, add a condition to check if the day's `High` price has crossed the `profit_target_price`.
        d. If the profit target is hit, the exit is triggered. The `exit_price` must be the `profit_target_price` itself (not the day's high) to ensure a conservative and deterministic exit simulation. This exit takes precedence over the max holding period.
*   **Time estimate:** 5 hours
*   **Status:** Done & Reverted

*   **Resolution & Learnings:**
    *   **Outcome:** The implementation was functionally correct, but the backtest revealed a catastrophic drop in all performance metrics (Sharpe Ratio, Annualized Returns, Profit Factor). The hypothesis that a symmetrical risk:reward target would improve performance was **conclusively falsified**.
    *   **Root Cause:** A fundamental mismatch between the strategy's nature and the exit logic was identified. Our system is a **mean-reversion** strategy that profits from short-term reversions to a statistical mean. The fixed reward:risk ratio is a **trend-following** exit concept. It forced the system to hold winning trades for too long, waiting for large, trend-like profit targets that rarely materialized, causing profitable trades to decay into smaller wins or even losses.
    *   **Final Action:** The changes from this task have been **reverted** from the codebase. The previous, simpler exit logic (ATR stop-loss or max holding period) proved more effective because it did not contradict the core statistical edge of the entry signal. A detailed post-mortem has been added to `docs/memory.md` to ensure this flawed approach is not attempted again.

---
### Task 25 — Create Universe Pre-Filtering Script for Strategy Specialization

*   **Rationale:** (Nadh) The backtest proved the strategy is a specialist. It works on `POWERGRID.NS` and fails everywhere else. Wasting CPU cycles backtesting a mean-reversion strategy on trending stocks like `RELIANCE.NS` is inefficient and violates the "fail fast" principle. The most pragmatic solution is not to change the algorithm, but to curate the universe it operates on. (Hinton) This is a form of dataset curation, a crucial step in any applied ML project. We are simplifying the problem for our model by pre-selecting a dataset where the signal-to-noise ratio for mean-reversion is inherently higher. This is valid, provided the selection is done on out-of-sample data to prevent selection bias from contaminating our final backtest results.
*   **Items to implement:**
    1.  **Create New Script:** Create a new, standalone script: `scripts/universe_analyzer.py`. This script will not be part of the main `praxis_engine` package.
    2.  **Script Logic:** The script should:
        a. Define a list of Nifty 500 tickers (this can be hardcoded or read from a simple text file).
        b. Define an out-of-sample date range for analysis (e.g., `2010-01-01` to `2017-12-31`), which does not overlap with the main backtest period.
        c. Loop through each stock ticker.
        d. Use the `DataService` to fetch historical data.
        e. Use the `hurst_exponent` function from `core/statistics.py` to calculate the Hurst exponent for the entire period.
        f. Store the results (ticker and Hurst value) in a list.
        g. After processing all stocks, sort the list by the Hurst exponent in ascending order.
        h. Print a clean, copy-paste-ready list of the top 50 tickers where `Hurst < 0.5`.
    3.  **Documentation:** Add a section to `README.md` explaining how to run this script to generate a curated stock list for `config.ini`.
*   **Tests to cover:**
    *   Given this is a one-off analysis script, a full test suite is over-engineering. The primary test is to run the script and manually verify that it produces a sensible, sorted list of tickers and their Hurst values.
*   **Acceptance Criteria (AC):**
    *   A new script exists that can analyze a list of stocks and identify the most mean-reverting candidates based on historical data.
    *   The output is a simple list of stock tickers that can be directly used to update the `stocks_to_backtest` parameter in `config.ini`.
*   **Definition of Done (DoD):**
    *   The script is created and functional. The `README.md` is updated with instructions for its use.
*   **Time estimate:** 3 hours
*   **Status:** Done

---
### Task 26 — Update Stock Universe with Curated List

*   **Rationale:** (Nadh) The `universe_analyzer.py` script (Task 25) was created to provide a data-driven list of mean-reverting stocks. The final step to operationalize this finding is to update the system's configuration to use this curated list. This ensures that the backtester's resources are focused only on the stocks where the strategy has the highest probability of being applicable, directly applying the key learning from previous, broader backtests.
*   **Items to implement:**
    1.  Run the `scripts/universe_analyzer.py` script to generate the list of mean-reverting tickers.
    2.  Copy the output list of tickers.
    3.  Open `config.ini` and replace the value of the `stocks_to_backtest` parameter in the `[data]` section with the new, curated list.
    4.  Run a full backtest using the `run.py backtest` command to confirm the system runs correctly with the new, specialized stock universe.
*   **Tests to cover:**
    *   The primary test is to run the backtester and ensure it completes without errors using the new stock list.
*   **Acceptance Criteria (AC):**
    *   The `config.ini` file is updated with a list of stocks identified as mean-reverting by the universe analyzer.
    *   A backtest run completes successfully using this new configuration.
*   **Definition of Done (DoD):**
    *   The `config.ini` file is updated and a successful backtest has been run.
*   **Time estimate:** 1 hour
*   **Status:** Done

---

## Epic 8: Performance & Scalability

*Goal: To transform the backtesting engine from a slow, single-threaded research tool into a high-performance system capable of rapidly analyzing hundreds of stocks. This epic addresses the critical performance bottlenecks identified in the initial implementation, making large-scale analysis and sensitivity testing feasible.*

---

### Task 27 — Parallelize Per-Stock Backtests with Multiprocessing

*   **Rationale:** (Nadh) The current single-threaded backtest is the most significant bottleneck for analyzing a large universe. The problem is "embarrassingly parallel," as each stock's backtest is independent. Leveraging all available CPU cores is the most pragmatic, highest return-on-investment change to achieve a near-linear speedup for the entire run without altering the core strategy logic.
*   **Items to implement:**
    1.  Modify the `backtest` command in `praxis_engine/main.py`.
    2.  Import Python's `multiprocessing.Pool`.
    3.  Create a top-level helper function that can be pickled by `multiprocessing`. This function will accept a stock ticker, create a new `Orchestrator` instance, and run the backtest for that single stock.
    4.  Replace the main `for` loop over the stock list with a call to `pool.imap_unordered` to distribute the work across all available CPU cores.
    5.  Integrate `tqdm` with the multiprocessing pool to ensure the progress bar continues to function correctly.
    6.  Collect the results from all parallel processes and run the existing aggregation and report generation logic.
*   **Tests to cover:**
    *   This is primarily a functional test. The key validation is to run a backtest on a small, fixed set of stocks (e.g., 4-8) both before and after the change on a multi-core machine.
    *   **Assertion 1:** The parallel version must complete significantly faster.
    *   **Assertion 2:** The final generated `backtest_summary.md` must be numerically identical to the one from the single-threaded run.
*   **Acceptance Criteria (AC):**
    *   The `backtest` command utilizes multiple CPU cores during execution.
    *   A full backtest on the configured universe completes in a fraction of the original time.
    *   The final aggregated report is identical to the one produced by a single-threaded run, ensuring correctness.
*   **Definition of Done (DoD):**
    *   The `main.py` backtest command is refactored to use `multiprocessing.Pool`. The system correctly utilizes parallel processing, and the results are verified to be correct.
*   **Time estimate:** 4 hours
*   **Status:** Done

---

### Task 28 — Accelerate Numerical Hotspots with Numba JIT

*   **Rationale:** (Hinton/Nadh) Profiling reveals that specific, pure-Python numerical functions, like the Hurst exponent calculation, are computational hotspots within each backtest. While vectorization is preferred, some algorithms are inherently loopy. Instead of a costly rewrite in C, we can use Numba to Just-In-Time (JIT) compile these critical Python functions into highly optimized machine code. This is a targeted, surgical optimization that provides C-like speed for the parts of the code that need it most.
*   **Items to implement:**
    1.  Add `numba` to the project's `requirements.txt`.
    2.  **Profile:** Use a profiler (e.g., `cProfile`) to confirm the primary numerical bottlenecks during a single-stock run. The `hurst_exponent` function in `core/statistics.py` is the primary suspect.
    3.  **Refactor for Numba:**
        a. In `core/statistics.py`, import `numba`.
        b. Decorate the `hurst_exponent` function (or another identified bottleneck) with `@numba.jit(nopython=True)`.
        c. Modify the function to work with NumPy arrays instead of Pandas Series. The calling code must be updated to pass `series.to_numpy()`.
        d. Ensure all code inside the decorated function is compatible with Numba's `nopython` mode, refactoring to basic loops or supported NumPy functions if necessary.
*   **Tests to cover:**
    *   The existing unit tests for `hurst_exponent` in `tests/test_statistics.py` must continue to pass, verifying the numerical correctness of the JIT-compiled version.
    *   (Optional but recommended) Add a benchmark test using `pytest-benchmark` to formally measure and assert the performance gain of the Numba-fied function against the original.
*   **Acceptance Criteria (AC):**
    *   At least one identified computational bottleneck is successfully accelerated with the `@numba.jit` decorator.
    *   The backtest produces identical numerical results (within a small tolerance for floating-point differences).
    *   The overall runtime for a single stock backtest is measurably reduced due to the optimization.
*   **Definition of Done (DoD):**
    *   The `numba` dependency is added. The target function is refactored, decorated, and fully tested for both correctness and performance improvement.
*   **Time estimate:** 6 hours
*   **Status:** Done

---

### Task 29 — Pre-calculate All Indicators to Eliminate O(N^2) Loop Inefficiency

*   **Rationale:** (Nadh) A performance profile of the backtester reveals a classic and entirely avoidable `O(N^2)` inefficiency. The main walk-forward loop recalculates all technical indicators (BBands, RSI, ATR) over an expanding data window on *every single iteration*. This is computationally wasteful. On day 1000, we are re-doing the work of day 999 plus one extra day. The pragmatic solution is to perform one, single, vectorized `O(N)` calculation for all indicators before the loop begins. This is the lowest-hanging fruit for performance optimization.
*   **Items to implement:**
    1.  **Orchestrator Refactoring:** In `praxis_engine/core/orchestrator.py`, within the `run_backtest` method, before the main `for` loop:
        a. Call all necessary indicator functions (`bbands`, `rsi`, `atr` from `core/indicators.py`) on the `full_df`.
        b. This will generate several `pd.Series` or `pd.DataFrame` objects containing the indicator values for the entire backtest period.
        c. Use `pd.concat` to merge these new indicator columns into the `full_df`.
    2.  **Signal Engine Signature Change:** Modify the `generate_signal` method in `praxis_engine/services/signal_engine.py`.
        a. Its signature must change from `generate_signal(self, df_daily: pd.DataFrame)` to `generate_signal(self, full_df_with_indicators: pd.DataFrame, current_index: int)`.
        b. All internal logic that calculates indicators must be removed.
        c. The logic must be rewritten to perform simple lookups on the provided dataframe at the `current_index` (e.g., `latest_daily = full_df_with_indicators.iloc[current_index]`).
    3.  **Validation Service Signature Change:** The same refactoring pattern must be applied to the guards that perform calculations (specifically `StatGuard`).
        a. The `validate` methods in the guards should now accept the `full_df_with_indicators` and `current_index`.
        b. The `StatGuard` must be updated to look up pre-calculated Hurst and ADF values. This will require pre-calculating these statistics using a `rolling().apply()` method in the `Orchestrator` to ensure point-in-time correctness.
    4.  **Orchestrator Loop Update:** The main loop in `run_backtest` must be updated to call the refactored services with the new signatures, passing the complete dataframe and the current loop index `i`.
*   **Tests to cover:**
    *   **Correctness Test (Critical):** Run a full backtest on a single, deterministic stock (e.g., `POWERGRID.NS` from 2018-2020) *before* the changes. Save the resulting list of `Trade` objects. After implementing the changes, run the exact same backtest. The new list of `Trade` objects must be numerically identical to the saved list. This proves the refactoring did not alter the strategy's logic.
    *   **Performance Benchmark:** Add a simple timer (`time.time()`) around the `run_backtest` call for a single stock. Assert that the execution time after the refactoring is at least 5x faster than before.
    *   Update unit tests for `SignalEngine` and `ValidationService` to reflect their new method signatures.
*   **Acceptance Criteria (AC):**
    *   The backtester produces numerically identical trade results to the pre-refactoring version.
    *   The runtime for a single-stock backtest over a 10-year period is significantly reduced.
*   **Definition of Done (DoD):**
    *   All indicator calculations are moved out of the main loop. All relevant services are refactored to use lookups instead of calculations. All existing tests pass, and new correctness and performance tests are added.
*   **Time estimate:** 8 hours
*   **Status:** Done
*   **Resolution:** The O(N^2) inefficiency has been eliminated. The `Orchestrator` now calls a `precompute_indicators` function once per stock. The `SignalEngine`, `ValidationService`, and `StatGuard` have been fully refactored to remove all on-the-fly calculation logic and legacy code paths. They now exclusively use efficient O(1) lookups on the pre-computed dataframe, adhering to the architecture. This completes the performance refactoring outlined in this task.

---

## Epic 9: Intelligent Exit Logic Refinement

*Goal: To address the core flaw of the passive exit strategy by introducing a profit-taking mechanism that is philosophically consistent with the mean-reversion entry signal. This epic aims to drastically reduce drawdown and improve the Sharpe Ratio by closing trades once their statistical edge has been realized, rather than holding them and re-introducing market risk.*

---

### Task 30 — Implement Mean-Reversion Profit Target Exit (Exit at Middle Bollinger Band)

*   **Rationale:** (Hinton) The current exit logic is asymmetrical. We have a rule for when we are wrong (ATR stop-loss) but no rule for when we are right, leading to profit decay and catastrophic drawdowns. The strategy's entire premise is reversion to the mean. Therefore, the most scientifically sound exit is the moment this reversion occurs. (Nadh) This is the most pragmatic and simplest effective change. It replaces an arbitrary timeout with a data-driven, dynamic target (the mean) that is already being calculated. This aligns the exit with the entry thesis, completing the strategy's logical loop with minimal code complexity.
*   **Items to implement:**
    1.  **Configuration:** In `config.ini`, add a new boolean parameter to the `[exit_logic]` section: `use_mean_reversion_exit = True`.
    2.  **Models:** In `core/models.py`, add the corresponding `use_mean_reversion_exit: bool` field to the `ExitLogicConfig` Pydantic model.
    3.  **Orchestrator Logic:** Modify the `Orchestrator._determine_exit` method in `core/orchestrator.py`.
        a. Inside the day-by-day forward loop that checks for the stop-loss, add a new profit-taking condition that only runs if `use_mean_reversion_exit` is true.
        b. This condition must check if the day's `High` price has crossed above the pre-computed middle Bollinger Band (`BBM`). The column name (e.g., `BBM_15_2.0`) should be constructed dynamically using parameters from the config.
        c. If the target is hit, the exit is triggered. The `exit_price` should be the `BBM` value for that day to ensure a conservative and deterministic simulation.
        d. The order of checks within the loop must be: 1. ATR Stop-Loss, 2. Mean-Reversion Profit Target, 3. Max Holding Days Timeout.
*   **Tests to cover:**
    *   In `tests/test_orchestrator.py`, create a new integration test with a synthetic DataFrame where a trade is initiated.
    *   The synthetic price series should be designed to cross the `BBM` on a specific day *before* hitting the ATR stop-loss or the `max_holding_days` timeout.
    *   Assert that the trade exits on the correct day and that the `exit_price` passed to the `ExecutionSimulator` is the `BBM` value for that day.
    *   Create a second test where the price hits the ATR stop-loss *before* reaching the `BBM`, and assert that the stop-loss exit correctly takes precedence.
*   **Acceptance Criteria (AC):**
    *   The backtester can be configured via `config.ini` to use the new mean-reversion exit logic.
    *   When enabled, trades correctly exit upon the price touching the middle Bollinger Band, and this exit takes precedence over the max holding period timeout.
*   **Definition of Done (DoD):**
    *   All new code is implemented, the `config.ini` is updated, and new integration tests are written and passing.
*   **Time estimate:** 4 hours
*   **Status:** Done & Reverted
*   **Resolution & Learnings:** The implementation was functionally correct, but the "exit at the mean" hypothesis was scientifically flawed for this strategy. Backtests showed that exiting at the mean (`BBM`) systematically cut off the most profitable part of the reversion, collapsing the average win rate and destroying the strategy's edge. The hypothesis was **conclusively falsified**. This flawed logic was replaced by the symmetrical exit logic in **Task 35**, which targets the upper Bollinger Band, allowing the reversion to complete its cycle.

---

## Epic 10: Architectural Refactoring & Performance Alignment

*Goal: To correct the architectural flaws in the `sensitivity_analysis` implementation. The current serial, stateful approach in the `Orchestrator` is a performance bottleneck and an architectural inconsistency. This epic refactors the feature to align with the high-performance, parallel, and stateless patterns established in the primary `backtest` command, making it a genuinely useful tool for rapid, large-scale experimentation.*

---

### Task 31 — Refactor Sensitivity Analysis Orchestration from Orchestrator to CLI

*   **Rationale:** (Nadh) The current implementation makes the `Orchestrator` stateful by having it modify its own configuration inside a loop. This is a code smell and violates `[H-2]`. The responsibility for orchestrating a multi-run experiment belongs in the CLI entry point (`main.py`), not in the core engine. This task moves the "looping" logic to the correct layer of abstraction.
*   **Items to implement:**
    1.  **Create New Top-Level Helper:** In `praxis_engine/main.py`, create a new top-level function `run_backtest_for_stock_with_config(payload: Tuple[str, Config])`. This function will be picklable by `multiprocessing`. It will accept a stock ticker and a complete `Config` object, instantiate a *new* `Orchestrator`, and run a single backtest.
    2.  **Move Parameter Loop to CLI:** In `praxis_engine/main.py`, refactor the `sensitivity_analysis` command function. It will now contain the primary loop that iterates through the parameter values defined in `config.ini`.
    3.  **Isolate Configurations:** Inside this loop, for each parameter value, create a `copy.deepcopy()` of the base configuration object. This ensures that each parallel run receives a clean, isolated configuration, preventing any state leakage.
    4.  **Modify Config Copy:** Use the `_set_nested_attr` helper to modify the parameter value in the copied config object.
    5.  **Aggregation Logic:** The `_aggregate_trades` method is a helper within the `Orchestrator`. The CLI function will need to call it. The most pragmatic solution is to instantiate a temporary, stateless `Orchestrator` at the end of each parameter loop *only* to call this aggregation helper.
*   **Tests to cover:**
    *   This is a structural refactoring. The primary validation will be in the subsequent tasks. The key is that the system remains logically functional after this move.
*   **Time estimate:** 3 hours
*   **Status:** Done
*   **Resolution:** The stateful `run_sensitivity_analysis` loop was moved from the `Orchestrator` to the `sensitivity_analysis` command in `main.py`. The logic is now stateless, creating isolated config objects for each run. Helper functions were moved from the Orchestrator to `utils.py` and `main.py` to support this.

---

### Task 32 — Parallelize Sensitivity Analysis Stock Runs

*   **Rationale:** (Nadh/Hinton) The most critical flaw is the serial execution of per-stock backtests within the sensitivity analysis. This is an "embarrassingly parallel" problem that we have already solved correctly in the `backtest` command. Failing to apply the same solution here is an architectural failure that makes the feature too slow to be scientifically useful. This task implements the required parallelization.
*   **Items to implement:**
    1.  **Integrate `multiprocessing.Pool`:** In the refactored `sensitivity_analysis` command in `main.py`, within the main parameter loop, use `multiprocessing.Pool`.
    2.  **Distribute Work:** For each parameter value, create a list of payloads `zip(stock_list, repeat(run_config))` and pass it to `pool.imap_unordered`, using the new `run_backtest_for_stock_with_config` helper.
    3.  **Progress Bar:** Integrate `tqdm` to provide a progress bar for the parallel execution of stocks *within* each parameter step, giving the user clear feedback on the progress.
*   **Tests to cover:**
    *   This is primarily a functional and performance test. The correctness will be verified in Task 36.
*   **Time estimate:** 2 hours
*   **Status:** Done
*   **Resolution:** The per-stock backtest loop within the sensitivity analysis was parallelized using `multiprocessing.Pool` and the `imap_unordered` pattern, mirroring the implementation of the main `backtest` command.

---

### Task 33 — Deprecate and Remove `Orchestrator.run_sensitivity_analysis`

*   **Rationale:** (Nadh) Prefer deletion over abstraction. The logic for running the sensitivity analysis now lives entirely in `praxis_engine/main.py`. The old method in the `Orchestrator` is now redundant, stateful, and inefficient. It must be removed to prevent confusion and to enforce the new, correct architecture. Every line is a liability.
*   **Items to implement:**
    1.  **Delete Method:** In `praxis_engine/core/orchestrator.py`, delete the entire `run_sensitivity_analysis` method.
    2.  **Delete Test:** In `tests/test_orchestrator_analysis.py`, delete the test file or the specific tests that cover the now-removed method.
*   **Tests to cover:**
    *   The test suite must continue to pass after the deletion, proving that no other part of the system depended on this method.
*   **Time estimate:** 1 hour
*   **Status:** Done
*   **Resolution:** The `run_sensitivity_analysis` method was deleted from `praxis_engine/core/orchestrator.py` and the corresponding test file `tests/test_orchestrator_analysis.py` was also deleted.

---

### Task 34 — Add Correctness and Performance Verification for Sensitivity Analysis

*   **Rationale:** (Hinton) A refactoring of this magnitude requires rigorous verification. We must prove two things: 1) The new, parallel implementation produces numerically identical results to the old, serial one, ensuring the scientific integrity of the experiment is preserved. 2) The new implementation is significantly faster, justifying the refactoring effort.
*   **Items to implement:**
    1.  **Correctness Test:**
        a. Before implementing the changes, run a sensitivity analysis on a small, fixed set of parameters and 2-4 stocks (e.g., `POWERGRID.NS`, `ITC.NS`).
        b. Save the generated `sensitivity_analysis_report.md` as a baseline (e.g., `sensitivity_analysis_report_baseline.md`).
        c. After implementing Tasks 33-35, run the exact same analysis.
        d. The newly generated report must be a character-for-character match with the baseline file. This is the ground truth.
    2.  **Performance Benchmark:**
        a. On a multi-core machine, time the execution of the baseline run from step 1a.
        b. Time the execution of the new, parallel implementation from step 1c.
        c. The new implementation must be demonstrably faster (e.g., at least 2x faster on a 4-core machine for 4 stocks).
*   **Tests to cover:**
    *   This task *is* the test. The acceptance criteria are the successful completion of the correctness and performance checks.
*   **Time estimate:** 2 hours
*   **Status:** Done
*   **Resolution:** A baseline was established by running the old implementation on 4 stocks (runtime: 5m 26s). The new, parallelized implementation was run on the same configuration, and the resulting report was identical. The new runtime was 3m 3s, confirming a significant performance improvement.

---

### Task 35 — Refactor Exit Logic to Target Upper Bollinger Band

*   **Rationale:** (Hinton) The current exit logic implemented in Task 30 is the primary cause of the strategy's failure. It is scientifically incoherent, as it exits a mean-reversion trade at the mean itself, systematically cutting off the most profitable part of the reversion. This is proven by the backtest data, which shows the average win collapsing from a profitable 11.62% to a disastrous 3.19%. (Nadh) This task replaces the flawed logic with a simple, robust, and symmetrical exit. The entry is a bet on reversion *from* the lower band; the exit should logically target the *upper* band. This aligns the exit with the entry thesis, completes the strategy's logical loop, and does so with minimal code complexity by reusing an already calculated indicator.
*   **Items to implement:**
    1.  **Configuration:** In `config.ini`, within the `[exit_logic]` section, rename the `use_mean_reversion_exit` parameter to `use_symmetrical_bb_exit` and ensure it is set to `True`.
    2.  **Models:** In `core/models.py`, update the `ExitLogicConfig` Pantic model to reflect this name change, removing `use_mean_reversion_exit` and adding `use_symmetrical_bb_exit: bool`.
    3.  **Orchestrator Logic:** Modify the `Orchestrator._determine_exit` method in `praxis_engine/core/orchestrator.py`.
        a. Remove the logic that targets the middle Bollinger Band (`BBM`).
        b. Implement a new profit-taking condition that runs if `use_symmetrical_bb_exit` is true.
        c. This condition must check if the day's `High` price has crossed *above* the pre-computed **upper** Bollinger Band (`BBU`). The column name (e.g., `BBU_15_2.0`) must be constructed dynamically from the config parameters.
        d. If the target is hit, the `exit_price` must be the `BBU` value for that day to ensure a conservative and deterministic simulation.
        e. The order of checks within the loop must be strictly maintained: 1. ATR Stop-Loss, 2. Symmetrical BB Profit Target, 3. Max Holding Days Timeout.
*   **Tests to cover:**
    *   In `tests/test_orchestrator.py`, create a new integration test with a synthetic DataFrame.
    *   **Scenario 1:** The synthetic price series must be designed to cross the `BBU` on a specific day *before* hitting the ATR stop-loss or the `max_holding_days` timeout. Assert that the trade exits on the correct day and that the `exit_price` is the `BBU` value for that day.
    *   **Scenario 2:** Create a second test where the price hits the ATR stop-loss *before* reaching the `BBU`, and assert that the stop-loss exit correctly takes precedence.
*   **Time estimate:** 4 hours
*   **Status:** Done

---

### Task 36 — Add Post-Mortem for Flawed Exit Logic to Project Memory

*   **Rationale:** (Hinton) A failed experiment is only a waste if nothing is learned. The catastrophic performance drop caused by the "exit at the mean" logic is a critical data point. We must document this finding to ensure this flawed hypothesis is not re-tested in the future. (Nadh) The old code and configuration represent a liability. Now that the logic is replaced, we must remove the obsolete artifacts and record the reason in `docs/memory.md`. This keeps the codebase clean and the project's institutional knowledge sharp.
*   **Items to implement:**
    1.  **Update `docs/tasks.md`:** Mark the original **Task 30** as `Done & Reverted`. Add a `Resolution & Learnings` section explaining that the implementation was functionally correct but strategically flawed, leading to its replacement by the logic in **Task 35**.
    2.  **Update `docs/memory.md`:** Create a new section titled "Task 30 & 35 Learnings: The Importance of Symmetrical Exits".
        a. Briefly describe the "exit at the mean" hypothesis from Task 30.
        b. State clearly that the backtest **falsified** this hypothesis.
        c. Include the key evidence: the collapse of the average win from `11.62%` to `3.19%` while the average loss remained stable, destroying the risk/reward profile.
        d. Conclude with the primary lesson: "A strategy's exit logic must be philosophically and mathematically consistent with its entry signal's statistical premise. For mean reversion, this means allowing the reversion to complete its cycle."
*   **Tests to cover:**
    *   The full test suite must continue to pass after any related code cleanup, ensuring no regressions were introduced.
*   **Time estimate:** 1 hour
*   **Status:** Done

---

### Task 37 — Revert Flawed Symmetrical BB Exit Logic (Task 35)

*   **Rationale:** (Nadh) The exit logic implemented in Task 35, which targets the upper Bollinger Band, has been identified as the primary cause of the system's poor risk-adjusted returns (Sharpe 0.87, MDD -65.13%). It creates an asymmetrical risk/reward profile where the profit target is a moving, volatility-dependent variable, while the stop-loss is fixed at entry. This is an uncontrolled and unnecessarily complex system. (Hinton) The backtest data proves this hypothesis is flawed. We must revert it to establish a clean baseline before testing a more scientifically sound alternative. Prefer deletion over retaining flawed code.
*   **Items to implement:**
    1.  **Configuration:** In `config.ini`, delete the `use_symmetrical_bb_exit` parameter from the `[exit_logic]` section.
    2.  **Models:** In `core/models.py`, remove the `use_symmetrical_bb_exit: bool` field from the `ExitLogicConfig` Pydantic model.
    3.  **Orchestrator Logic:** In `praxis_engine/core/orchestrator.py`, within the `_determine_exit` method, completely remove the conditional block that checks for and implements the upper Bollinger Band profit target.
    4.  **Tests:** In `tests/test_orchestrator.py`, delete the tests that specifically verify the BBU exit logic (`test_run_backtest_symmetrical_bb_exit_triggered` and `test_run_backtest_atr_takes_precedence_over_symmetrical_bb`).
*   **Tests to cover:**
    *   The full test suite must pass after these removals, ensuring no regressions were introduced.
*   **Time estimate:** 2 hours
*   **Status:** To Do

---

### Task 38 — Implement Symmetrical, Fixed Risk/Reward Profit Target

*   **Rationale:** (Hinton) This task directly addresses the core flaw of an asymmetrical risk profile. By making the profit target a fixed multiple of the risk taken at entry, we create a controlled, scientifically testable exit strategy. (Nadh) This is the most pragmatic solution. It replaces a complex, unpredictable moving target with a simple, deterministic rule. It makes the system's risk management explicit and auditable for every trade. This is a re-test of the concept from the reverted Task 24, but correctly paired with the robust ATR-based stop-loss, which is a valid and necessary experiment.
*   **Items to implement:**
    1.  **Configuration:** In `config.ini`, add a new parameter to the `[exit_logic]` section: `reward_risk_ratio = 1.75`.
    2.  **Models:** In `core/models.py`, add the corresponding `reward_risk_ratio: float` field to the `ExitLogicConfig` Pydantic model.
    3.  **Orchestrator Logic:** Refactor the `Orchestrator._determine_exit` method in `core/orchestrator.py`.
        a. After calculating the `stop_loss_price`, immediately calculate the risk: `risk_per_share = entry_price - stop_loss_price`.
        b. Calculate the fixed profit target: `profit_target_price = entry_price + (risk_per_share * self.config.exit_logic.reward_risk_ratio)`.
        c. Inside the day-by-day forward loop, add a new condition to check if the day's `High` price has crossed the `profit_target_price`.
        d. If the target is hit, the `exit_price` must be the `profit_target_price` itself (not the day's high) to ensure a conservative and deterministic simulation.
        e. The order of checks within the loop must be strictly maintained: 1. ATR Stop-Loss, 2. Fixed Profit Target, 3. Max Holding Days Timeout.
*   **Tests to cover:**
    *   In `tests/test_orchestrator.py`, create a new integration test with a synthetic DataFrame.
    *   **Scenario 1:** The synthetic price series must be designed to cross the calculated `profit_target_price` *before* hitting the ATR stop-loss. Assert that the trade exits on the correct day and that the `exit_price` is the `profit_target_price`.
    *   **Scenario 2:** Create a second test where the price hits the ATR stop-loss *before* reaching the profit target, and assert that the stop-loss exit correctly takes precedence.
*   **Time estimate:** 4 hours
*   **Status:** To Do

---

### Task 39 — Add Post-Mortem for Flawed BBU Exit to Project Memory

*   **Rationale:** (Hinton) A failed experiment is only a waste if the learning is not recorded. The catastrophic performance of the "exit at the upper band" logic is a critical data point that falsified a plausible-sounding hypothesis. We must document this finding to ensure this flawed approach is not re-tested. (Nadh) This is about maintaining the project's institutional knowledge and adhering to the "Don't repeat stupid mistakes" principle.
*   **Items to implement:**
    1.  **Update `docs/tasks.md`:** Mark **Task 35** as `Done & Reverted`. Add a `Resolution & Learnings` section explaining that the BBU target created an uncontrolled, asymmetrical risk profile and was replaced by the fixed R:R logic in **Task 39**.
    2.  **Update `docs/failed_experiments.md`:** Create a new entry for the "Symmetrical Exit at Upper Bollinger Band" experiment.
        a. **Hypothesis:** State the original idea: "Since the entry is at the lower band, a symmetrical exit at the upper band should capture the full reversion cycle."
        b. **Outcome & Evidence:** State clearly that the backtest **conclusively falsified** this hypothesis. Quote the key evidence from `backtest_summary.md`: Sharpe Ratio of 0.87 and Max Drawdown of -65.13%, with an `Avg. Win` of only +6.35% compared to the baseline's +11.62%.
        c. **Root Cause Analysis:** Explain the "moving target" problem. The BBU expands with volatility, pushing the profit target further away and creating an unfavorable risk/reward ratio, especially in volatile conditions.
        d. **Lesson Learned:** An exit must be symmetrical to the *risk taken at entry*, not just conceptually symmetrical to the entry indicator. A fixed profit target based on the initial stop-loss distance provides a more robust and controllable risk management framework.
*   **Time estimate:** 1 hour
*   **Status:** To Do

