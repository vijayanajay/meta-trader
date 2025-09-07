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

### Task 16 — Instrument Backtest Runs with Reproducibility Metadata
* Rationale: Backtests are experiments; stamp each run with deterministic metadata.
* Implemented: Git-hash helper, Orchestrator captures timestamp/config/git-hash, report adds a "Run Configuration & Metadata" table.
* Resolution: Reports are self-describing and reproducible.
* Status: Done

---

### Task 17 — Signal Attrition Funnel & Guardrail Rejection Tracking
* Rationale: If we don't measure what we filter, we can't improve it.
* Implemented: Orchestrator counts potential_signals, rejections_by_guard, rejections_by_llm, trades_executed; ReportGenerator emits funnel and rejection tables.
* Resolution: Full funnel instrumentation with tests; shows where signals are dropped.
* Status: Done

---

### Task 18 — Per‑Stock Performance Breakdown
* Rationale: Averages hide where the strategy actually works; need per‑stock granularity.
* Implemented: `run_backtest` returns per‑stock results (trades + rejection counts); CLI aggregates; report includes per‑stock table.
* Resolution: Per‑stock diagnostics available for pruning and specialization.
* Status: Done

---

### Task 19 — Trade Distribution & Statistical Analysis
* Rationale: Distributional shape (skew/kurtosis) and outliers matter more than the mean.
* Implemented: KPIs via Pandas (skew, kurtosis, avg win/loss, holding period) and ASCII histogram utility; integrated into report.
* Resolution: Distribution diagnostics added for deeper insight into return character.
* Status: Done

---

### Task 20 — LLM Performance Uplift Analysis
* Rationale: Measure whether the LLM actually improves strategy outcomes.
* Implemented: Orchestrator collects `pre_llm_trades` and `final_trades` and LLM scores; ReportGenerator computes uplift and renders score histogram.
* Resolution: LLM impact is measurable; supports cost/benefit decisions.
* Status: Done

---

### Task 21 — Align Task Numbers with Descriptions
* Rationale: Numbering drift causes confusion between requests and docs.
* Implemented: Reviewed and aligned task numbers and descriptions across docs.
* Resolution: Task references are consistent.
* Status: Done

---

### Task 22 — Harden LLM API Connectivity
* Rationale: Transient API failures must not halt backtests.
* Implemented: Retries with exponential backoff, timeouts, and improved logging in `LLMAuditService`.
* Resolution: LLM calls are resilient to transient network errors; tests added for retry behavior.
* Status: Done

---

### Task 23 — Update PRD and Other Documentation
* Rationale: Docs must reflect current implementation and dependencies.
* Implemented: Planned updates to `docs/prd.md`, `docs/memory.md`, and `README.md` to mention OpenRouter/Kimi2 and recent findings.
* Resolution: Documentation updates scheduled.
* Status: To Do

---

### Task 24 — Dynamic Profit Target (Reward:Risk)
* Rationale: Test a fixed reward:risk to control asymmetry in exits.
* Implemented: `reward_risk_ratio` added to config and exit logic; deterministic profit-target exit added with ATR stop-loss precedence; tests added.
* Resolution: Reverted after backtests showed worse performance; post‑mortem recorded in `docs/memory.md`.
* Status: Done & Reverted

---

### Task 25 — Universe Pre‑Filtering Script
* Rationale: Specialize the universe to stocks where mean‑reversion works to save CPU and improve edge.
* Implemented: `scripts/universe_analyzer.py` computes Hurst on out‑of‑sample data and prints top mean‑reverting tickers; README instructions added.
* Resolution: Script produces a curated ticker list usable in `config.ini`.
* Status: Done

---

### Task 26 — Update Stock Universe with Curated List
* Rationale: Operationalize curated universe to focus resources where strategy applies.
* Implemented: Run analyzer to produce list, update `config.ini`, run backtest to validate configuration.
* Resolution: `config.ini` updated and backtest completed successfully with curated universe.
* Status: Done

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
*   **Status:** Done & Reverted
*   **Resolution & Learnings:** The BBU target created an uncontrolled, asymmetrical risk profile and was replaced by the fixed R:R logic in **Task 38**.

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
*   **Status:** Done

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
*   **Status:** Done

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
*   **Status:** Done

## Epic 11: From Data to Diagnosis — The Trade Log

*Goal: To instrument the backtesting engine to produce a detailed, machine-readable log of every simulated trade. This log is not just for debugging; it is the primary dataset for understanding the root causes of system performance, particularly catastrophic drawdowns. We will achieve this by creating an enriched `Trade` model and a CSV export pipeline that is fully compatible with our parallel architecture, while simultaneously using this opportunity to refactor and accelerate our reporting logic.*

---

### Task 40 — Extend the `Trade` Model for Deeper Analysis

*   **Rationale:** (Hinton) To diagnose failure, we need to record the state of the system at the time of the decision. The current `Trade` model only records the outcome, not the conditions that led to it. We must enrich it to capture the *why* of the entry and the *how* of the exit. (Nadh) The most direct way to do this is to add fields to the existing Pydantic model. It's the smallest change that provides the required data downstream.
*   **Items to implement:**
    1.  In `praxis_engine/core/models.py`, modify the `Trade` model to include the following new fields:
        *   `exit_reason: str` (e.g., "ATR_STOP_LOSS", "PROFIT_TARGET", "MAX_HOLD_TIMEOUT")
        *   `liquidity_score: float`
        *   `regime_score: float`
        *   `stat_score: float`
        *   `composite_score: float`
        *   `entry_hurst: float`
        *   `entry_adf_p_value: float`
        *   `entry_sector_vol: float`
*   **Tests to cover:**
    *   Update any tests that create `Trade` objects to include the new required fields. This will likely cause initial test failures, which is a good thing—it forces us to update our test fixtures to the new contract.
*   **Time estimate:** 1 hour
*   **Status:** Done

---

### Task 41 — Refactor `_determine_exit` to Return Exit Reason

*   **Rationale:** (Nadh) The `_determine_exit` function is the only place in the system that knows the precise reason for an exit. Currently, it only returns the date and price, discarding this critical piece of context. This is an information leak. We must refactor it to return the reason alongside the outcome.
*   **Items to implement:**
    1.  In `praxis_engine/core/orchestrator.py`, change the return signature of `_determine_exit` from `-> Tuple[Optional[pd.Timestamp], Optional[float]]` to `-> Tuple[Optional[pd.Timestamp], Optional[float], str]`.
    2.  Inside the method, when an exit condition is met, return the corresponding reason string.
        *   If `current_day["Low"] <= stop_loss_price`, return `(current_day.name, stop_loss_price, "ATR_STOP_LOSS")`.
        *   If `current_day["High"] >= profit_target_price`, return `(current_day.name, profit_target_price, "PROFIT_TARGET")`.
        *   For the final timeout condition, return `(..., ..., "MAX_HOLD_TIMEOUT")`.
*   **Tests to cover:**
    *   Update the tests in `tests/test_orchestrator.py` that cover exit logic (`test_run_backtest_atr_exit_triggered`, etc.) to assert that the correct exit reason string is being returned by the (now mocked) `_determine_exit` method.
*   **Time estimate:** 2 hours
*   **Status:** Done

---

### Task 42 — Update Orchestrator to Create Enriched `Trade` Objects

*   **Rationale:** (Hinton/Nadh) Now that the data is available, we must plumb it through the system. The `Orchestrator` is the central point where the signal scores and the exit reason are both available. This is the logical place to assemble the complete, enriched `Trade` object.
*   **Items to implement:**
    1.  In `praxis_engine/core/orchestrator.py`, modify the `_simulate_trade_from_signal` method.
        a. It will now receive the `ValidationScores` object as an argument.
        b. It will call the refactored `_determine_exit` and unpack the new three-part tuple: `exit_date, exit_price, exit_reason`.
    2.  Modify the `run_backtest` loop. When it calls `_simulate_trade_from_signal`, it must now pass the `scores` object.
    3.  In `_simulate_trade_from_signal`, when calling `self.execution_simulator.simulate_trade`, pass all the new data points (`exit_reason`, scores, etc.) so they can be used to construct the enriched `Trade` object. This will require updating the signature of `simulate_trade` and the `Trade` constructor call within it.
    4.  We also need the raw inputs to the scores. The most pragmatic place to get these is from the pre-computed dataframe at the `current_index`. Pass these values (`hurst`, `adf`, `sector_vol`) through to the `Trade` object constructor.
*   **Tests to cover:**
    *   Update integration tests in `tests/test_orchestrator.py` to assert that the `Trade` objects being created and returned contain the correct, non-null values for the new fields.
*   **Time estimate:** 2 hours
*   **Status:** Done

---

### Task 43 — Implement CSV Export in `main.py` and Refactor Reporting for Performance

*   **Rationale:** (Nadh) This is the core implementation and a chance for a pragmatic performance win. The current process is inefficient: workers return lists of Pydantic objects, which are aggregated, then passed to the `ReportGenerator`, which iterates over them *again* to calculate KPIs. Now that we need a DataFrame for the CSV, we can make it the central data structure. The workers will return simple lists of dictionaries (faster to pickle and process), which the main process will concatenate into a single DataFrame. This DataFrame will then be passed to both the CSV writer and a refactored `ReportGenerator`, eliminating redundant data conversions and enabling vectorized calculations.
*   **Items to implement:**
    1.  **Worker Function:** In `praxis_engine/main.py`, modify `run_backtest_for_stock`. Instead of returning `{"trades": List[Trade], ...}`, it should now return `{"trades": List[Dict], ...}`, where each dictionary is the result of `trade.model_dump()`.
    2.  **CLI Aggregation:** In the `backtest` command in `main.py`, change the aggregation logic.
        a. Collect all the trade dictionaries from the worker processes into a single list.
        b. Convert this list into a `pd.DataFrame`: `trade_df = pd.DataFrame(all_trade_dicts)`.
        c. Save this DataFrame to a CSV file: `trade_df.to_csv("results/trade_log.csv", index=False)`.
    3.  **Performance Refactoring:**
        a. Modify the `ReportGenerator.generate_backtest_report` signature to accept the `trade_df: pd.DataFrame` instead of `trades: List[Trade]`.
        b. Refactor the `_calculate_kpis` method to work directly on the DataFrame. Replace list comprehensions with faster, vectorized Pandas operations (e.g., `trade_df['net_return_pct'].sum()` instead of `sum([t.net_return_pct for t in trades])`).
*   **Expected Performance Gain:** For a backtest with thousands of trades, replacing object iteration with vectorized Pandas operations can yield a **5-10x speedup** for the reporting phase. While this phase is not the main bottleneck, it's a "free" optimization that makes the code cleaner and more scalable, a classic Nadh win.
*   **Tests to cover:**
    *   Create a new test that runs the `backtest` CLI command (mocking the orchestrator) and asserts that `results/trade_log.csv` is created and is not empty.
    *   Update `tests/test_report_generator.py` to pass a sample DataFrame to the refactored methods and assert that the calculated KPIs are still correct.
*   **Time estimate:** 3 hours
*   **Status:** Done


---

### The `trade_log.csv` Column Specification

**(Hinton):** The CSV is our ground truth dataset for future analysis. Its schema must be explicit and comprehensive.

| Column Name | Data Type | Description | Rationale |
| :--- | :--- | :--- | :--- |
| `stock` | string | The stock ticker (e.g., "POWERGRID.NS"). | Basic trade identification. |
| `entry_date` | datetime | The timestamp of the trade entry. | For time-series analysis. |
| `exit_date` | datetime | The timestamp of the trade exit. | For time-series analysis. |
| `holding_period_days` | integer | The number of calendar days the trade was held. | To analyze the character of returns. |
| `entry_price` | float | The simulated entry price (including slippage & costs). | Core performance metric. |
| `exit_price` | float | The simulated exit price (including slippage & costs). | Core performance metric. |
| `net_return_pct` | float | The net percentage return of the trade after all costs. | The ultimate success metric for the trade. |
| `exit_reason` | string | The rule that triggered the exit ("ATR_STOP_LOSS", "PROFIT_TARGET", "MAX_HOLD_TIMEOUT"). | **The most critical new column for drawdown analysis.** |
| `composite_score` | float | The final composite score (product of all guard scores) at entry. | Quantifies the quality of the signal at entry. |
| `liquidity_score` | float | The liquidity guard score (0.0-1.0) at entry. | To analyze if low-liquidity signals are problematic. |
| `regime_score` | float | The regime guard score (0.0-1.0) at entry. | To analyze if trades taken in marginal regimes are failing. |
| `stat_score` | float | The statistical guard score (0.0-1.0) at entry. | To analyze if statistically weaker signals are failing. |
| `entry_hurst` | float | The raw Hurst exponent value at the time of entry. | Raw data for deeper analysis of the `StatGuard`. |
| `entry_adf_p_value` | float | The raw ADF p-value at the time of entry. | Raw data for deeper analysis of the `StatGuard`. |
| `entry_sector_vol` | float | The raw sector volatility (%) at the time of entry. | Raw data for deeper analysis of the `RegimeGuard`. |
| `config_bb_length` | integer | The `bb_length` from `config.ini` for this run. | Makes the log self-contained for future analysis. |
| `config_rsi_length` | integer | The `rsi_length` from `config.ini` for this run. | Makes the log self-contained for future analysis. |
| `config_atr_multiplier` | float | The `atr_stop_loss_multiplier` from `config.ini`. | Makes the log self-contained for future analysis. |

---

### Task 44 — Restore Architectural Purity by Reverting Flawed Service Move

*   **Rationale:** (Nadh/Hinton) A previous refactoring in **Task 38** moved I/O-bound services (`DataService`, `ExecutionSimulator`) into the pure `core/` directory. This was a critical architectural error that directly violated the non-negotiable hard rule `[H-12]`, which mandates that all I/O be confined to `services/`. This task reverts that change to restore the strict separation of concerns, ensuring the core engine remains pure, offline-testable, and aligned with the project's foundational principles.
*   **Items to implement:**
    1.  **Move Files:** Move `data_service.py` and `execution_simulator.py` from `praxis_engine/core/` back to `praxis_engine/services/`.
    2.  **Update Imports:** Update all import statements across the codebase that referenced the incorrect locations.
    3.  **Verify:** Run the full test suite to ensure the refactoring did not introduce any regressions.
*   **Status:** Done
*   **Resolution:** The services were moved back to the `services/` directory, all import paths were corrected, and the full test suite (`70 passed`) confirmed the change was successful. The architectural integrity of the `core` module is restored.

## Epic 12: Drawdown Diagnostics & Root Cause Analysis

*Goal: (Hinton) The system's `-67.03%` maximum drawdown is not a simple statistic; it is the signature of a critical failure mode. Our objective is to move from knowing *that* it failed to understanding precisely *why* it failed. (Nadh) This is a diagnostic epic. We will not modify the core strategy. We will build simple, pragmatic tools to dissect the `trade_log.csv`—the flight recorder of our backtest—to isolate the exact trades, conditions, and reasons that led to this catastrophic capital bleed. We build the microscope first, then we perform the surgery.*

---

### Task 45 — Create Standalone Drawdown Analysis Script

*   **Rationale:** (Nadh) The fastest path to an answer is a standalone script. We will not touch the core engine. We will build a simple, powerful tool that ingests the `trade_log.csv` and performs the two most critical initial analyses: identifying which `exit_reason` is causing the most damage and isolating the exact sequence of trades that constitute the maximum drawdown. This is maximum insight for minimum code.
*   **Items to implement:**
    1.  **Create New Script:** Create a new, standalone script: `scripts/analyze_drawdown.py`. It should use `typer` for a clean CLI, accepting the path to `trade_log.csv` as an argument.
    2.  **Load Data:** The script must load the specified CSV into a `pandas` DataFrame. It must handle `FileNotFoundError` gracefully.
    3.  **Implement Exit Reason Analysis (Option 2):**
        a. Group the DataFrame by the `exit_reason` column.
        b. For each reason, calculate the `count`, `sum`, and `mean` of the `net_return_pct`.
        c. Format and print this summary into a clean, human-readable table. This will immediately show if `ATR_STOP_LOSS` is the primary source of losses.
    4.  **Implement Equity Curve & Drawdown Isolation (Option 3):**
        a. Ensure the DataFrame is sorted by `exit_date`.
        b. Calculate the equity curve by taking the cumulative product of `(1 + net_return_pct)`.
        c. Calculate the running maximum of the equity curve (`.cummax()`).
        d. Calculate the drawdown series: `(equity_curve - running_max) / running_max`.
        e. Find the date of the maximum drawdown (the trough): `trough_date = drawdown.idxmin()`.
        f. Find the date of the peak *before* the trough: `peak_date = equity_curve.loc[:trough_date].idxmax()`.
        g. Filter the original trade log to get only the trades that occurred between `peak_date` and `trough_date`.
        h. Print a header "Trades within Maximum Drawdown Period" and display this filtered DataFrame.
*   **Tests to cover:**
    *   This is a one-off analysis script. A full test suite is over-engineering. The primary test is to run the script on the existing `results/trade_log.csv` and manually verify that it produces a sensible equity curve and correctly identifies the drawdown trades.
*   **Time estimate:** 3 hours
*   **Status:** Done

---

### Task 46 — Enhance Analysis Script with Drawdown Cohort Analysis

*   **Rationale:** (Hinton) We have isolated the problematic trades. Now, we must find the common features among them. This task enhances our diagnostic script to perform a cohort analysis on the drawdown trades, grouping them by their entry conditions. This is how we move from observing the failure to forming a data-driven hypothesis about its root cause.
*   **Items to implement:**
    1.  **Modify `scripts/analyze_drawdown.py`:** This task builds directly on Task 45.
    2.  **Isolate Drawdown Trades:** Use the logic from Task 45 to get the `drawdown_trades_df`.
    3.  **Implement Cohort Analysis (Option 4):**
        a. **Group by Stock:** Group the `drawdown_trades_df` by `stock` and aggregate the count and sum of `net_return_pct` to see if specific stocks are responsible.
        b. **Bin and Group by Scores/Volatility:**
            i.  Use `pd.cut` to create bins for `composite_score` (e.g., 4 bins from 0.0 to 1.0).
            ii. Use `pd.cut` to create bins for `entry_sector_vol` (e.g., `[0, 15, 22, 100]`).
            iii.Group by these new bins and aggregate the count and sum of returns.
    4.  **Output:** After printing the drawdown trades list, print these new cohort analysis tables with clear headers (e.g., "Drawdown Analysis by Stock", "Drawdown Analysis by Composite Score").
*   **Tests to cover:**
    *   Again, the test is the output. Run the enhanced script and verify that the cohort tables are generated correctly and provide clear, actionable insights into the characteristics of the failing trades.
*   **Time estimate:** 2 hours
*   **Status:** Done

---

### Task 47 — Refactor Drawdown Logic into a Reusable Diagnostics Service

*   **Rationale:** (Nadh) The script has proven its value. Now, we extract the pure analysis logic from the script's I/O and encapsulate it in a proper, testable service. This is a critical step before integrating it into the main engine. The logic for calculating a drawdown is a reusable piece of analytics; it does not belong in a one-off script or tangled inside the `ReportGenerator`. This adheres to `[H-2]` (Stateless Services) and `[H-30]` (Follow The Architecture).
*   **Items to implement:**
    1.  **Create New Models:** In `praxis_engine/core/models.py`, create new Pydantic models to structure the output:
        ```python
        class DrawdownPeriod(BaseModel):
            start_date: pd.Timestamp
            end_date: pd.Timestamp
            peak_value: float
            trough_value: float
            max_drawdown_pct: float
            trade_indices: List[int] # Indices from the original DataFrame
        ```
    2.  **Create New Service:** Create a new file: `praxis_engine/services/diagnostics_service.py`.
    3.  **Implement `analyze_drawdown`:** Create a class `DiagnosticsService` with a static method `analyze_drawdown(trades_df: pd.DataFrame) -> Optional[DrawdownPeriod]`.
        a. Move the equity curve and drawdown calculation logic from the script (Task 45) into this method.
        b. The method should accept a DataFrame of trades and return a `DrawdownPeriod` object (or `None` if no trades).
    4.  **Refactor Script:** Update `scripts/analyze_drawdown.py` to import and use this new `DiagnosticsService`. The script now becomes a simple wrapper that loads a CSV and calls the service, keeping the logic clean and separate.
*   **Tests to cover:**
    *   Create a new test file: `tests/test_diagnostics_service.py`.
    *   Create a unit test with a sample DataFrame of trades containing a known drawdown.
    *   Call `DiagnosticsService.analyze_drawdown` and assert that the returned `DrawdownPeriod` object has the correct start/end dates, drawdown percentage, and trade indices.
*   **Time estimate:** 3 hours
*   **Status:** Done

---

### Task 48 — Integrate Drawdown Analysis into the Final Report

*   **Rationale:** (Hinton/Nadh) The diagnostic logic is now a robust, tested service. The final step is to plumb it into the main reporting pipeline. This makes the drawdown analysis an automatic, zero-effort part of every backtest run. The system will now self-diagnose its worst failure mode on every execution, making our iteration loop faster and more scientifically rigorous. This is the definition of a mature diagnostic tool.
*   **Items to implement:**
    1.  **Modify `ReportGenerator`:** In `praxis_engine/services/report_generator.py`:
        a. Import the `DiagnosticsService` and the `DrawdownPeriod` model.
        b. In the `generate_backtest_report` method, after the KPIs are calculated, call `DiagnosticsService.analyze_drawdown(trades_df)`.
    2.  **Create New Report Section:**
        a. Create a new private method `_generate_drawdown_analysis_section(self, trades_df: pd.DataFrame, drawdown_period: Optional[DrawdownPeriod]) -> str`.
        b. This method will check if `drawdown_period` is not `None`.
        c. If it exists, it will filter `trades_df` using the `trade_indices` from the `drawdown_period` object.
        d. It will then format a new Markdown section titled "### Maximum Drawdown Analysis", showing the period's stats (start, end, percentage) and a summary table of the trades *within* that drawdown (e.g., count, total return, breakdown by `exit_reason`).
    3.  **Append to Report:** In `generate_backtest_report`, append the string returned by the new method to the main report string, just after the KPI table.
*   **Tests to cover:**
    *   Update `tests/test_report_generator.py`.
    *   Create a new test that passes a sample `trades_df` to `generate_backtest_report`.
    *   Assert that the final report string contains the "Maximum Drawdown Analysis" header and a table with the correct data for the drawdown trades.
*   **Time estimate:** 2 hours
*   **Status:** Done

---

## Epic 13: The Market Weather Station — An Automated Regime Meta-Model

*Goal: (Hinton) To address the primary flaw of the system—its inability to recognize a market-wide trending regime—by replacing the simplistic, single-factor `RegimeGuard` with a more robust, multi-factor classification model. (Nadh) We will build this as a self-contained, automated subsystem. The backtester will now be responsible for ensuring the regime model is trained and available before execution, removing the need for manual intervention or configuration flags. The system becomes self-sufficient.*

---

### Task 49 — Create a Market-Wide Data Service

*   **Rationale:** (Nadh) The meta-model needs market-wide data, not per-stock data. This is a fundamentally different concern from the existing `DataService`. The first, simplest step is to create a new, dedicated service to fetch and cache this data. This adheres to the Single Responsibility Principle and `[H-12]`.
*   **Items to implement:**
    1.  **Create New Service:** Create a new file: `praxis_engine/services/market_data_service.py`.
    2.  **Implement Fetch Logic:** Inside a `MarketDataService` class, create a method `get_market_data(tickers: List[str], start: str, end: str)`. This method will use `yfinance` to download data for market indices like `^NSEI` (Nifty 50) and `^INDIAVIX` (India VIX).
    3.  **Implement Caching:** Add Parquet-based caching logic, identical to the existing `DataService`, to avoid re-fetching data on every run.
    4.  **Configuration:** Add a new `[market_data]` section to `config.ini` to specify the index and VIX tickers, and the date range for training data (e.g., `training_start_date = "2010-01-01"`).
*   **Tests to cover:**
    *   Create a new test file: `tests/test_market_data_service.py`.
    *   Write a unit test that mocks `yfinance.download` and verifies that the service correctly fetches, caches, and loads data from the cache.
*   **Time estimate:** 3 hours
*   **Status:** Done
*   **Resolution (Reviewer):** Confirmed. A new `MarketDataService` was created in `praxis_engine/services/` to handle fetching and caching of market-wide data. The implementation adheres to architectural principles (`[H-12]`) and is fully unit-tested with mocked I/O, following project best practices.

---

### Task 50 — Implement Feature Engineering for Market Regime

*   **Rationale:** (Hinton) Raw market data is not what the model learns from; it learns from engineered features that represent the state of the market. This logic must be pure, deterministic, and testable. (Nadh) We will place this pure logic in the `core/` directory, completely separate from the I/O-bound services.
*   **Items to implement:**
    1.  **Create New Module:** Create a new file: `praxis_engine/core/features.py`.
    2.  **Implement Feature Functions:** Create a function `calculate_market_features(market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame`. This function will take the raw data from `MarketDataService` and compute features such as:
        *   `nifty_vs_200ma`: The ratio of the Nifty 50 closing price to its 200-day simple moving average.
        *   `vix_level`: The raw value of the India VIX.
        *   `vix_roc_10d`: The 10-day rate-of-change of the VIX.
    3.  The function must return a single, date-indexed DataFrame containing all the calculated features.
*   **Tests to cover:**
    *   Create a new test file: `tests/test_features.py`.
    *   Write unit tests for `calculate_market_features` with a sample input DataFrame and assert that the output features are calculated correctly.
*   **Time estimate:** 2 hours
*   **Status:** Done
*   **Resolution (Reviewer):** Confirmed. A new pure function `calculate_market_features` was created in `praxis_engine/core/features.py`. The logic is clean, deterministic, and correctly placed in the `core` module as per the architecture. The function is well-tested with clear, specific assertions.

---

### Task 51 — Refactor Model Training Logic into a Reusable Function

*   **Rationale:** (Nadh) The training logic must be isolated but also callable from our main application. We will refactor the standalone script into a module with a primary, importable function. This keeps the core engine lean while allowing the CLI to orchestrate the training process when necessary.
*   **Items to implement:**
    1.  **Add Dependency:** Add `scikit-learn` and `joblib` to `requirements.txt`.
    2.  **Create/Refactor Script:** Create `scripts/train_regime_model.py`.
    3.  **Implement `train_and_save_model` function:**
        *   Define a function `train_and_save_model(config: Config) -> bool`.
        *   Inside this function, place all the logic for data loading (`MarketDataService`), feature engineering (`calculate_market_features`), and defining the target variable (`y`).
        *   Train a simple `LogisticRegression` model.
        *   Save the trained model to a predictable path defined in the config (e.g., `results/regime_model.pkl`).
        *   The function should return `True` on success and `False` on failure.
    4.  **Add CLI Entry Point:** In the same script, add an `if __name__ == "__main__":` block that loads the config and calls `train_and_save_model`. This allows the script to be run manually for debugging or retraining.
*   **Tests to cover:**
    *   This is primarily tested by its integration in the following tasks. The manual run capability serves as a functional test.
*   **Time estimate:** 4 hours
*   **Status:** Done
*   **Resolution:** Re-implemented the `scripts/train_regime_model.py` script to be robust and configurable. Added the `[regime_model]` section to `config.ini` and updated the Pydantic models accordingly. Added missing dependencies to `requirements.txt`. Added a functional test for the script and fixed all related test failures in the suite. The script now runs successfully and saves a trained model.

---

### Task 52 — Implement a Resilient, Fallback-Aware Regime Model Service

*   **Rationale:** (Nadh) The backtester must not crash if the model file is missing. The service responsible for using the model must be robust. It should attempt to load the model, and if it fails, it must log a clear warning and fall back to a neutral, non-blocking behavior.
*   **Items to implement:**
    1.  **Create New Service:** Create `praxis_engine/services/regime_model_service.py`.
    2.  **Implement Resilient `__init__`:**
        *   The `__init__` method will take the model path from the config.
        *   It will use a `try...except FileNotFoundError` block to load the model with `joblib.load`.
        *   If the file is found, it stores the model in `self.model`.
        *   If the file is **not** found, it sets `self.model = None` and logs a clear `log.warning`.
    3.  **Implement `predict_proba`:**
        *   The method will check `if self.model is None`.
        *   If the model is missing, it will return a neutral probability of `1.0` (indicating a "good regime"), ensuring it doesn't block any trades. This makes the model an optional enhancement rather than a hard dependency.
        *   If the model exists, it will use `self.model.predict_proba()` and return the probability of the "good regime" class.
*   **Tests to cover:**
    *   Create `tests/test_regime_model_service.py`.
    *   Test the service's behavior when the model file *does not* exist. Assert that `self.model` is `None` and that `predict_proba` returns `1.0`.
    *   Test the service's behavior when a dummy model file *does* exist. Assert that `predict_proba` calls the mock model's method.
*   **Time estimate:** 3 hours
*   **Status:** Done

---

### Task 53 — Automate the "Train-if-Needed" Workflow in the CLI

*   **Rationale:** (Nadh) This is the core of the automation. The `backtest` command itself will now be responsible for ensuring the model exists before starting the parallel workers. This logic belongs in the main process, at the highest level of orchestration, to ensure it runs only once.
*   **Items to implement:**
    1.  **Modify `main.py`:** In the `backtest` command function in `praxis_engine/main.py`.
    2.  **Add Model Path:** Define the expected path to the model file (e.g., `model_path = Path("results/regime_model.pkl")`).
    3.  **Implement Check-and-Train Logic:**
        *   **Before** the `multiprocessing.Pool` is created, add the check: `if not model_path.exists():`.
        *   If the model is missing, `log.info("Regime model not found. Attempting to train a new one...")`.
        *   Import the training function: `from scripts.train_regime_model import train_and_save_model`.
        *   Call the function: `success = train_and_save_model(config)`.
        *   If `success` is `False`, log a critical error and exit gracefully, as the backtest cannot proceed as intended without a model if one was expected.
    4.  **Configuration:** Remove the `use_regime_model` flag from `config.ini`. The presence of the model file now implicitly controls the behavior.
*   **Tests to cover:**
    *   This is an integration test. In `tests/test_workers.py` (or a new CLI test file), create a test for the `backtest` command.
    *   Mock `Path.exists` to return `False`.
    *   Patch `scripts.train_regime_model.train_and_save_model`.
    *   Run the CLI command and assert that the `train_and_save_model` function was called.
*   **Time estimate:** 2 hours
*   **Status:** Done
*   **Resolution:** Implemented the "train-if-needed" logic directly into the `backtest` CLI command in `main.py`. The command now checks for the existence of the model file (path specified in `config.ini`) before starting the backtest. If the model is missing, it automatically calls the `train_and_save_model` script. The `--force-retrain` flag was removed to simplify the CLI, making the file's presence the sole trigger. An integration test (`test_backtest_cli_trains_model_if_not_exists`) was added to `tests/test_workers.py` to verify this behavior.

---

### Task 54 — Integrate the New Regime Model and Validate Performance

*   **Rationale:** (Hinton) The system is now fully integrated. The final step is to run a rigorous backtest to scientifically validate whether this new, automated subsystem has solved the core problem of catastrophic drawdowns.
*   **Items to implement:**
    1.  **Refactor `RegimeGuard`:** The guard must now be instantiated with the `RegimeModelService` and use it to get its score. The old `sector_vol` logic should be removed or kept as a fallback if the model service returns a neutral score.
    2.  **Run Full Backtest:** Execute the `backtest` command. This will trigger the automatic training (if the model file is deleted first) and then run the full backtest using the newly trained model.
    3.  **Analyze Results:** Compare the new `backtest_summary.md` against the baseline. The primary success metric is a significant reduction in Maximum Drawdown, especially during the 2020 period.
    4.  **Document:** Update `docs/architecture.md` to reflect the new services and the automated training flow. Write a post-mortem in `docs/memory.md` or `failed_experiments.md` detailing the outcome of this epic.
*   **Acceptance Criteria (AC):**
    *   Running `python run.py backtest` with no `regime_model.pkl` present successfully trains and saves a model before executing the backtest.
    *   The Maximum Drawdown in the final report is significantly reduced compared to the baseline.
*   **Time estimate:** 2 hours
*   **Status:** Not Started

---
### Reviewer's Note on Epic 13 (2025-09-06)
*   **Finding:** Epic 13 is critically incomplete. While the foundational data components (Tasks 49, 50) are done, the core logic for training, serving, and integrating the regime model (Tasks 51-54) is either a stub or not started.
*   **Impact:** The system's primary advertised improvement—the automated regime meta-model—does not exist in the current codebase. The `RegimeGuard` still uses the old, simplistic sector volatility logic.
*   **Path Forward:** The remaining tasks (51-54) must be implemented to complete the epic. This involves:
    1.  Implementing the model training and saving logic in `scripts/train_regime_model.py`.
    2.  Creating the `RegimeModelService` as specified in Task 52.
    3.  Implementing the "train-if-needed" workflow in the CLI (Task 53).
    4.  Refactoring the `RegimeGuard` to use the new service and validating the performance uplift (Task 54).