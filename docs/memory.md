# Memory

This file is intended to store any issues, bugs, or important findings that are discovered during the development process. This is to ensure that we do not repeat the same mistakes and that we have a record of the decisions made.

## Task 1 Learnings

During the initial project scaffolding, the following issues were identified and resolved:

1.  **Pydantic Deprecation:** The `Config.parse_obj()` method is deprecated in Pydantic v2. It was replaced with `Config.model_validate()` to remove test warnings and stay current with the library's API.

2.  **Strict Typing with `mypy`:** The `--strict` flag for `mypy` requires type hints for all functions, including test functions. Return types (`-> None`) and argument types (`tmp_path: Path`) were added to all functions to satisfy the static analyzer and adhere to `[H-1]`.

3.  **`configparser` Formatting:** The `configparser` library does not support multi-line values out of the box unless they are indented. The `sector_map` dictionary in `config.ini` was moved to a single line to resolve parsing errors.

4.  **Python Module Imports:** Running `python praxis_engine/main.py` caused `ModuleNotFoundError` because the project root was not in the `PYTHONPATH`. This was resolved by making the project installable by adding the `[tool.poetry.packages]` section to `pyproject.toml` and then installing it in editable mode with `pip install -e .`.

5.  **Typer CLI Invocation:** There is an unresolved issue with invoking `typer` commands via `python -m praxis_engine.main verify-config` or `python praxis_engine/main.py verify-config`. This has been documented as **Task 1.1** to be investigated further.

## Task 3 & 8 Learnings

1.  **`pandas-ta` Incompatibility:** The `pandas-ta` library was found to be incompatible with the installed version of `numpy`, causing `ImportError`s. The library was removed and the required indicators (RSI, Bollinger Bands) were implemented manually using `pandas`. This reduces external dependencies and increases stability.

2.  **`hurst` Library:** The initial custom implementation of the Hurst exponent was flawed and produced incorrect results. The `hurst` library was added as a dependency to provide a correct and robust implementation.

3.  **`pyarrow` Dependency:** The `pandas` `to_parquet` and `read_parquet` functions require a backend engine. `pyarrow` was added as a dependency to provide this functionality.

4.  **`OpenAI` Client Mocking:** When testing the `LLMAuditService`, the `openai.OpenAI` client needs to be mocked. The correct way to do this is to patch the client where it is *used* (`praxis_engine.services.llm_audit_service.OpenAI`), not where it is defined (`openai.OpenAI`). Additionally, environment variables for the API key and base URL must be mocked for the client to be instantiated without errors.

5.  **`yfinance` Multi-level Index:** The `yfinance` library can return DataFrames with multi-level column indexes, which can cause issues with downstream processing. The code was made more robust by adding logic to flatten the column index after fetching data. After discussion with the user, this was deemed unnecessary complexity for the current use case and was removed in favor of a simpler implementation.

## Task 9 Learnings

1.  **Dependency Mismatch:** Test failures in `DataService` were caused by a `Missing optional dependency 'pyarrow'` error. The dependency was listed in `requirements.txt` but not in `pyproject.toml`, which was the source of truth for the test environment. This highlighted a structural issue in dependency management. The fix was to consolidate all dependencies into `pyproject.toml` and remove unused packages.

2.  **Structural Flaw in Data Processing Pipeline:** The `SignalEngine` was failing tests because it made incorrect assumptions about the data it received from `DataService`.
	*   **Issue:** `SignalEngine` used `.dropna()` immediately after resampling a dataframe. However, `DataService` calculates `sector_vol` using a rolling window, which introduces `NaN` values at the beginning of the series. When `SignalEngine` resampled the data, these initial `NaN`s caused the first resampled rows to be dropped, shortening the dataframe and causing subsequent length checks to fail.
	*   **Fix:** The aggressive `.dropna()` calls were removed. A more precise check was added to ensure the *final row* of data used for signal generation (`latest_daily`, `latest_weekly`, `latest_monthly`) did not contain any `NaN`s after all indicators were calculated.
	*   **Lesson:** Data integrity assumptions between services are a common source of structural bugs. Downstream services must be robust to the actual data shape produced by their upstream dependencies, including artifacts like `NaN`s from rolling calculations. Avoid aggressive, broad-stroke data cleaning (`.dropna()`) in the middle of a pipeline; instead, apply specific checks where they are needed.

3.  **Model Definition Bug:** A copy-paste error in `core/models.py` resulted in duplicated fields within the `DataConfig` Pydantic model. This was a simple bug but underscores the need for careful review. It was fixed by removing the duplicate lines.

## Task 10 & 11 Learnings

1.  **Redundant Dependency Files:** The project contained both a `pyproject.toml` and a `requirements.txt`, creating two sources of truth for dependencies. This led to a test environment that was missing packages (`pyarrow`) specified in `pyproject.toml` but not correctly installed, because other workflows might have been using the outdated `requirements.txt`. This is a critical structural flaw in maintaining reproducible environments.
	*   **Fix:** The `requirements.txt` file was deleted, establishing `pyproject.toml` as the single source of truth for all project dependencies, managed by Poetry. Unused dependencies were also removed from `pyproject.toml` to keep the dependency tree clean.
	*   **Lesson:** A project must have a single, authoritative source for its dependencies. For modern Python projects using tools like Poetry or PDM, this is `pyproject.toml`. Redundant files like `requirements.txt` should be removed to prevent environment inconsistencies.

2.  **Structural Flaw in Unit Testing:** The `DataService` tests were failing due to a missing `pyarrow` dependency in the test environment. While the root cause is environmental, this exposed a structural flaw in the tests themselves: they were integration tests masquerading as unit tests, with a hard dependency on the filesystem and the `parquet` serialization engine.
	*   **Fix:** The tests for `DataService` were refactored to mock all filesystem and serialization interactions (`pandas.DataFrame.to_parquet`, `pandas.read_parquet`, `pathlib.Path.exists`). This isolates the service's logic (fetching, processing, caching decisions) from the implementation details of the cache, making the tests more robust, faster, and independent of specific library installations.
	*   **Lesson:** Unit tests for services that perform I/O should mock the I/O boundary. This ensures the test is verifying the service's logic, not the correctness of the I/O library or the state of the filesystem.

3.  **Structural Flaw in Timeframe Alignment & Validation:** The `SignalEngine` was failing to generate signals due to two related structural issues:
	*   **Issue 1 (Temporal Misalignment):** It was using `df.iloc[-1]` on resampled weekly/monthly dataframes. This is only correct if the last day of the daily data happens to be a week/month-end. On any other day, the engine was comparing current daily data with indicator values from a past period, leading to incorrect signal evaluation.
	*   **Issue 2 (Overly Broad Validation):** A generic data validation check (`latest_row.isnull().any()`) would discard a valid signal if *any* column in the aligned weekly/monthly row was `NaN`. This is a common occurrence for columns generated by rolling calculations (like Bollinger Bands) near the start of a dataset.
	*   **Fix:** The logic was changed from `iloc[-1]` to `df.asof(last_daily_date)` to correctly select the last available row from the higher timeframe at or before the daily timestamp. The generic `.isnull().any()` check was replaced with a precise check that verifies only the *specific columns required for the signal decision* are not `NaN`.
	*   **Lesson:** When combining multiple timeframes, naive indexing is a common and critical bug. Use robust methods like `asof()` to ensure temporal integrity. Furthermore, data validation must be specific to the data required for the immediate downstream logic; broad checks are brittle and hide the true data requirements of a function.
## Task 10 Learnings

1.  **Redundant Dependency Files:** The project contained both a `pyproject.toml` and a `requirements.txt`, creating two sources of truth for dependencies. This led to a test environment that was missing packages (`pyarrow`) specified in `pyproject.toml` but not correctly installed, because other workflows might have been using the outdated `requirements.txt`. This is a critical structural flaw in maintaining reproducible environments.
	*   **Fix:** The `requirements.txt` file was deleted, establishing `pyproject.toml` as the single source of truth for all project dependencies, managed by Poetry. Unused dependencies were also removed from `pyproject.toml` to keep the dependency tree clean.
	*   **Lesson:** A project must have a single, authoritative source for its dependencies. For modern Python projects using tools like Poetry or PDM, this is `pyproject.toml`. Redundant files like `requirements.txt` should be removed to prevent environment inconsistencies.

2.  **Structural Flaw in Timeframe Alignment:** The `SignalEngine` was failing to generate signals in tests because of a subtle temporal misalignment bug. It was using `df.iloc[-1]` on resampled weekly and monthly dataframes. This is only correct if the last day of the daily data happens to be a week-end and month-end. On any other day, the engine was comparing current daily data with indicator values from a past period (the last completed week or month), leading to incorrect signal evaluation.
	*   **Fix:** The logic was changed from `df_weekly.iloc[-1]` to `df_weekly.asof(last_daily_date)`. The `pandas.DataFrame.asof()` method correctly selects the last available row from the higher timeframe (e.g., weekly) at or before the timestamp of the lower timeframe (daily).
	*   **Lesson:** When combining multiple timeframes in a walk-forward analysis, naive indexing like `iloc[-1]` on resampled dataframes is a common and critical bug. Data from different timeframes must be explicitly and correctly aligned to the point-in-time of the decision. Use robust methods like `asof()` or `reindex(..., method='ffill')` to ensure temporal integrity and avoid lookahead bias.

## Task 12 Learnings

1.  **Structural Flaw in Timeframe Resampling and Alignment:** A subtle but critical bug was found in the `SignalEngine` that caused tests to fail by not generating signals when expected. The root cause was a temporal misalignment introduced during resampling.
	*   **Issue:** The code used `resample('W-FRI')` and `resample('ME')`, which label resampled data with the *end* of the period (e.g., the upcoming Friday or the last day of the month). When `asof(last_daily_date)` was used to get the latest weekly/monthly data, it would correctly look for the last row at or before the daily date. However, because the label for the current, incomplete period was in the future, `asof()` would select the data from the *previous, completed* period. This introduced a significant data lag, causing the engine to compare current daily data against stale weekly and monthly indicator values.
	*   **Fix:** The resampling logic was changed to use start-of-period labels: `resample('WS')` (Week Start) and `resample('MS')` (Month Start). This labels the data with the beginning of the period. Now, `asof()` correctly selects the data corresponding to the current, in-progress week and month, preserving point-in-time correctness.
	*   **Lesson:** Correct temporal alignment when mixing timeframes is paramount. Using `asof()` is necessary but not sufficient. The index labeling of the resampled data must also be point-in-time correct. For walk-forward analysis, using start-of-period labels (`WS`, `MS`) is a more robust pattern than end-of-period labels (`W-FRI`, `ME`).

## Task 5 Learnings

1.  **Typer CLI Bug:** The CLI fails with a `TypeError: Parameter.make_metavar() missing 1 required positional argument: 'ctx'` when run with `--help`. This issue was investigated, and several refactorings of the entry point scripts (`run.py`, `praxis_engine/main.py`) were attempted. The bug persists, suggesting a deeper issue within the Typer library version or its dependencies. As the core `backtest` command works correctly, further investigation was deprioritized in favor of maintaining functional progress. The recommended way to run the application is `poetry run python run.py [COMMAND]`.

## Backtesting Engine Refactoring Learnings

1.  **Critical Data Leakage in Backtester:** The `Orchestrator` was passing the entire historical DataFrame (including future data) to the `ExecutionSimulator`. The simulator was then using this future data to determine entry and exit prices. This is a severe form of lookahead bias that completely invalidates backtest results.
    *   **Fix:** The `ExecutionSimulator` was refactored to be a pure function. Its `simulate_trade` method was changed to no longer accept the full DataFrame. Instead, the `Orchestrator`, which simulates the passage of time, determines the exact entry/exit prices and dates from the full dataset and passes only these primitive values to the simulator.
    *   **Lesson:** The component responsible for simulating trade execution *must* be isolated from future data. Its API should enforce this by only accepting the data available at the moment of the trade. The orchestrator/backtest loop is the only component that should have access to the full timeline.

2.  **Incorrect Cost Model Implementation:** The `ExecutionSimulator`'s cost model did not match the PRD specifications. Brokerage was calculated with `min()` instead of `max()`, and the STT rate was incorrect. Furthermore, all cost parameters were hardcoded ("magic numbers").
    *   **Fix:** The cost calculations were corrected to match the PRD. All cost-related magic numbers were moved to a new `[cost_model]` section in `config.ini` and loaded via a corresponding `CostModelConfig` Pydantic model. The `ExecutionSimulator` was updated to receive this config during initialization.
    *   **Lesson:** All strategy and environment parameters, including cost models, must be centralized in a configuration file. This prevents magic numbers, makes the system easier to audit and modify, and enforces the "Configuration is Centralized and Immutable" rule (`[H-10]`).

3.  **Brittle Test Fixtures:** The test suite had multiple failures due to Pydantic `ValidationError`s. Test fixtures were creating model instances without providing all required fields, because the models had been updated since the tests were written.
    *   **Fix:** All test fixtures that create Pydantic models were updated to provide all required fields, resolving the validation errors. The mock config data in `test_config_service.py` was also updated.
    *   **Lesson:** When using Pydantic models for configuration and data structures, the test suite must be kept in sync with model changes. A failing test due to a missing required field is a feature, not a bug, as it correctly identifies that a component's data contract has changed.

4.  **Poetry Environment Mismatch:** Tests were failing with `ModuleNotFoundError` even after packages were installed with `pip`. This was because the project is managed by `poetry`, which uses its own virtual environment.
    *   **Fix:** The correct dependencies were installed using `poetry install`. Commands were then run within the poetry environment using `poetry run ...`.
    *   **Lesson:** When a project uses a dependency manager like `poetry` or `pdm`, all interactions (installing, running scripts, running tests) must be done through the manager's interface (e.g., `poetry run`) to ensure the correct virtual environment and dependencies are used.

## LLM Audit Service Implementation Learnings

1.  **Incomplete Service Implementation:** The `LLMAuditService` was using hardcoded placeholder values for historical statistics (win_rate, profit_factor, etc.) instead of calculating them. This made the LLM audit meaningless.
    *   **Fix:** Implemented a `_calculate_historical_performance` method within the service. This method runs a "mini-backtest" on the historical data window to compute real performance metrics, ensuring the LLM receives accurate data for its audit. This required injecting the `SignalEngine`, `ValidationService`, and `ExecutionSimulator` into the `LLMAuditService` and updating the `Orchestrator` to provide them.
    *   **Lesson:** A service's implementation must be complete and correct before it is integrated into the main application flow. Using placeholders is acceptable during initial development, but they must be replaced with real logic to fulfill the service's contract.

## LLM Audit Service Refactoring Learnings

1.  **Data Leakage in Historical Performance Calculation:** The initial implementation of `_calculate_historical_performance` within the `LLMAuditService` contained a subtle but critical data leakage bug. It was looking ahead in the dataframe to find the exit price (`df_window.iloc[i + exit_days]["Close"]`). This violates the core principle of walk-forward testing (`[H-21]`).
    *   **Fix:** The method was refactored to perform a correct point-in-time simulation. It now iterates up to `len(df_window) - exit_days` and only uses data available at index `i` to make a decision and simulate the trade. The cost calculation was delegated to a new pure function `execution_simulator.calculate_net_return` to ensure consistency with the main backtester.
    *   **Lesson:** Data leakage is an insidious bug that can hide in helper methods. Any calculation that simulates historical performance must be rigorously checked to ensure it only uses data that would have been available at that specific point in time.

2.  **Prompt Template Variable Mismatch:** The Jinja2 prompt template (`statistical_auditor.txt`) used the variable `{{ sector_volatility }}`, but the `LLMAuditService` was passing a dictionary with the key `sector_vol`. This would cause the template to render with a blank value for that statistic.
    *   **Fix:** The context dictionary created in `get_confidence_score` was updated to use the correct key, `sector_volatility`, matching the template.
    *   **Lesson:** When using templates (for prompts, reports, etc.), ensure there is a "contract" between the template placeholders and the code that generates the context. A simple unit test could have caught this by rendering the template and asserting that the output string contains the expected values.

3.  **Robust LLM Response Parsing:** The initial code used a naive `float(response)` to parse the LLM's output. This is brittle and would fail if the LLM returned any extra text, violating the principle of a constrained action space (`[H-25]`).
    *   **Fix:** A private helper method, `_parse_llm_response`, was implemented. It uses a regular expression to find the first floating-point number in the response string. It also includes error handling and clamps the final value between 0.0 and 1.0, ensuring the service always returns a valid score.
    *   **Lesson:** Never trust external service outputs. Always parse and validate responses from APIs, especially LLMs, to ensure they conform to the expected format. Defensive parsing prevents system failures due to unexpected or malformed responses.

## Execution Simulator Refinement Learnings

1.  **Inaccurate Task Documentation:** The main project task list (`docs/tasks.md`) incorrectly marked the `ExecutionSimulator` and its cost model (Tasks #6 and #10) as "Complete". However, code review revealed that the slippage model was only a placeholder (a fixed percentage) and not the volume-based model required by the PRD.
    *   **Fix:** The task list in `docs/tasks.md` was updated to mark the relevant tasks as "In Progress" to reflect the actual state of the codebase.
    *   **Lesson:** Documentation, especially task tracking, must be treated like code and kept rigorously in sync with the implementation. An out-of-date task list can hide significant remaining work and lead to incorrect project status assessments.

2.  **Previous Data Leakage Vulnerability:** An earlier version of the `ExecutionSimulator` contained a critical data leakage flaw where the `simulate_trade` function was passed the entire future price history to determine exits.
    *   **Fix:** The service was refactored into a pure component that receives only the necessary point-in-time data (entry/exit prices), with the `Orchestrator` being responsible for managing the timeline.
    *   **Lesson:** This is a recurring and critical theme. Services that simulate trade outcomes *must* have APIs that programmatically prevent access to future data. This architectural principle is non-negotiable for valid backtesting.

## Environment Refactoring Learnings

1.  **Removal of Poetry:** The project was initially set up to use Poetry for dependency management. This was causing issues and was not in line with the desired simple Python environment.
    *   **Fix:** All Poetry-related files (`poetry.lock`, `pyproject.toml`) were removed. The project now uses a simple environment with dependencies installed via `pip`.
    *   **Lesson:** The choice of dependency management tool should be appropriate for the project's needs and the user's preferences. A simple `pip` and `requirements.txt` (or in this case, just `pip install`) can be more straightforward for smaller projects or when explicit user preference is stated.

## Orchestrator Refactoring Learnings (Post-Review)

A full code review identified several critical, interacting flaws in the `Orchestrator` that undermined the validity and efficiency of the entire system.

1.  **Lookahead Bias in ATR Calculation:** The `run_backtest` method was calculating the ATR indicator on the *entire* dataframe (including future data) before starting the walk-forward loop. It also used `bfill()` to fill `NaN` values, which explicitly uses future data to fill past gaps. This is a subtle but severe form of lookahead bias (`[H-21]`) that invalidates the results of any strategy using the ATR-based exit.
    *   **Fix:** The ATR calculation was moved *inside* the main walk-forward loop. At each step `i`, the ATR is now calculated *only* on the `window` of data available up to that point. This makes the indicator calculation point-in-time correct and eliminates the lookahead bias.
    *   **Lesson:** Indicator calculations that involve smoothing or averaging (like ATR, moving averages, etc.) must be performed on the point-in-time data window within a backtest loop. Pre-calculating them on the full dataset is a common but critical error.

2.  **Catastrophic Inefficiency in Opportunity Generation:** The `generate_opportunities` method was designed to find signals on the most recent day. To get historical context for the LLM audit, it was running a full, separate backtest for each stock, for the entire lookback period. This was computationally explosive and architecturally unsound.
    *   **Fix:** The `generate_opportunities` method was completely rewritten to be lean and efficient. A new private helper, `_calculate_historical_stats_for_llm`, was created. The new flow is:
        1.  Check for a signal on the latest data point.
        2.  If (and only if) a signal is found and validated, call the new helper method to run a lean, focused backtest on the data *prior* to the signal date.
        3.  Use the returned stats for the LLM audit.
    *   **Lesson:** Avoid re-implementing or calling complex workflows (like a backtest) for simple sub-tasks. When a component needs a piece of data (like historical stats), create a dedicated, efficient function to generate exactly that data, rather than reusing a larger, more complex service that does more than required. This follows the Single Responsibility Principle.

## Task 13 Learnings

1.  **Test Environment Dependencies:** The test suite failed with `ModuleNotFoundError` for `statsmodels` and `openai`. This indicates that the initial dependency installation might be incomplete or that the test environment is not perfectly synchronized.
    *   **Fix:** The missing packages were installed manually using `pip`.
    *   **Lesson:** The dependency list, even when specified in a document like `HARD_RULES.md`, must be programmatically enforced. A `requirements.txt` or a more robust dependency management setup in `pyproject.toml` would prevent such issues. The project should standardize on a single, reliable method for environment setup.

2.  **Mocking Strategy for Complex Objects:** The initial test for the `run_sensitivity_analysis` method failed with a `TypeError` and then a `KeyError`. This was due to a flawed mocking strategy.
    *   **Issue:** The test initially tried to patch a method (`run_backtest`) on the `Orchestrator` class. However, the method being tested creates *new instances* of the `Orchestrator` within its loop. Accessing the `self` or `config` of these dynamically created instances via the mock's `call_args_list` proved difficult and brittle.
    *   **Fix:** The test was refactored to patch the *entire class* (`@patch('praxis_engine.core.orchestrator.Orchestrator')`). This allows the test to control the mock instances returned when `Orchestrator(...)` is called inside the method. The arguments passed to the constructor (specifically, the modified `config` object) can then be easily inspected via `MockOrchestrator.call_args_list[i].args[0]`.
    *   **Lesson:** When testing a method that instantiates and uses other objects of the same class, patching the class itself is often a more robust and cleaner approach than patching a method on the class. It provides better control and simplifies assertions about how those new instances are created and used.

3.  **Correctness of Test Assertions:** A test for the `_set_nested_attr` helper function was failing because it incorrectly expected an `AttributeError` to be raised for a non-existent attribute.
    *   **Issue:** The test asserted `with pytest.raises(AttributeError): _set_nested_attr(obj, "a.c", 99)`. However, Python's `setattr()` function creates the attribute if it doesn't exist, so no error is raised.
    *   **Fix:** The assertion was removed and replaced with a positive check to confirm that `setattr`'s behavior is handled correctly, as this behavior is acceptable for the function's purpose.
    *   **Lesson:** Ensure that test assertions match the actual, specified behavior of the code being tested and the underlying language features. A test can fail not because the code is wrong, but because the test's expectation is wrong.

## Task 14 Learnings

1.  **Environment and Dependency Management:** The test suite repeatedly failed with `ModuleNotFoundError` for packages like `statsmodels`, `openai`, `typer`, and `pyarrow`, even after `pip install` was run.
    *   **Issue:** This pointed to a classic environment mismatch, where the `pytest` runner was executing in a different context than the shell where `pip install` was run. The solution of chaining commands (`pip install ... && pytest`) ensures both commands run in the exact same shell session, resolving the issue.
    *   **Lesson:** For CI/CD and local testing, it is critical to ensure that dependency installation and script execution happen in the same, consistent environment. Chaining commands is a simple way to enforce this. A more robust solution is to use a script (`run_tests.sh`) that sets up the environment and runs the tests in one go.

2.  **Pydantic Model Validation in Tests:** After adding the new `scoring: ScoringConfig` field to the main `Config` model, multiple tests failed with Pydantic `ValidationError`.
    *   **Issue:** Test fixtures and helper functions were creating `Config` objects or loading `.ini` files that were now missing the required `scoring` section.
    *   **Lesson:** This is a feature, not a bug. Pydantic's strict validation immediately highlights all the places in the test suite that have become outdated due to a change in the data model. It enforces consistency between the application code and the test code.

3.  **Test Data Accuracy:** The unit test for the `LiquidityGuard`'s scoring logic was failing with an `AssertionError` because the expected score was incorrect.
    *   **Issue:** The test's input data (the `volume`) was off by a factor of 10, leading to a miscalculation of the turnover value used for scoring.
    *   **Lesson:** Test data, especially constants and magic numbers used to derive expected outcomes, must be as carefully reviewed as the application code itself. A small error in test data can lead to confusing failures and wasted debugging time.

4.  **Robust String Formatting:** A `TypeError` occurred in a `log.debug` statement within the `StatGuard` when trying to format a `None` value as a float (`f"{hurst:.2f}"`).
    *   **Issue:** The f-string format specifier `:.2f` cannot be applied to a `NoneType` object.
    *   **Fix:** The formatting was made safe by using a conditional expression within the f-string: `f"Hurst: {f'{hurst:.2f}' if hurst is not None else 'N/A'}"`.
    *   **Lesson:** Logging and other string formatting operations should always be defensive and account for the possibility of `None` values, especially for data coming from statistical functions or external sources that can fail.

5.  **Realistic Test Fixtures:** An integration test for the `ValidationService` failed with an `AttributeError` because it was using a simplified `pd.DataFrame` with a default integer index, while the code expected a `DatetimeIndex` to call `.date()`.
    *   **Fix:** The test was updated to create the DataFrame with a `DatetimeIndex`.
    *   **Lesson:** While unit tests should be simple, integration test fixtures should be as realistic as possible to catch errors related to data types and structures that might be missed with oversimplified mocks or dummies.
