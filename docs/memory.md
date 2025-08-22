# Development Memory & Learnings

This document logs key issues, their resolutions, and important learnings discovered during the development of the Self-Improving Quant Engine. The goal is to prevent revisiting solved problems.

---

### 1. `ModuleNotFoundError` during `pytest`

*   **Symptom:** Running `pytest` resulted in `ModuleNotFoundError: No module named 'services'` or `No module named 'core'`.
*   **Root Cause:** The test suite is run from the root directory, but the Python interpreter doesn't automatically know about the `src` directory where the application packages reside.
*   **Resolution:** The project must be installed in "editable" mode using `pip install -e .`. This creates a special link that makes the `src` package and its modules available throughout the virtual environment, allowing for clean imports like `from services.data_service import DataService`.
*   **Learning:** This setup is crucial for maintaining clean import paths and is a convention of the project. It was documented in `README.md` as part of Task 1.5.

---

### 2. `ImportError` for `pyarrow`

*   **Symptom:** Tests for `DataService` failed with `ImportError: Unable to find a usable engine; tried using: 'pyarrow', 'fastparquet'`.
*   **Root Cause:** The `pyarrow` dependency, required by `pandas` for writing Parquet files, was listed in `requirements.txt` but had not been installed in the environment. The initial dependency installation was done manually and was incomplete.
*   **Resolution:** Ran `pip install -r requirements.txt` to install all declared dependencies.
*   **Learning:** Always install dependencies from the `requirements.txt` file to ensure a consistent and complete environment.

---

### 3. `ImportError` for `pkg_resources`

*   **Symptom:** Tests failed with `ModuleNotFoundError: No module named 'pkg_resources'`.
*   **Root Cause:** The `pandas-ta` library has a dependency on `pkg_resources`, which is part of the `setuptools` package. In some newer Python environments, `setuptools` might not be installed by default or might be a minimal version.
*   **Resolution:** Explicitly installed `setuptools` using `pip install setuptools`.
*   **Learning:** Some libraries might have implicit dependencies that are not always declared or handled perfectly by `pip`.

---

### 4. `ImportError` for `numpy.NaN`

*   **Symptom:** Tests failed with `ImportError: cannot import name 'NaN' from 'numpy'`.
*   **Root Cause:** The installed version of `pandas-ta` (`0.3.14b0`) uses the `numpy.NaN` alias, which was deprecated and removed in `numpy` version 2.0. The environment had `numpy` 2.3.2 installed.
*   **Resolution:** Downgraded `numpy` to a version compatible with `pandas-ta`'s usage, specifically a version before 2.0. `pip install "numpy<2.0"` installed version 1.26.4, which resolved the issue.
*   **Learning:** Library incompatibilities, especially around major version updates (like `numpy` 2.0), are common. Pinning dependency versions or using a version resolver is crucial for stability. Patching the library was not an option as it was outside the repository.

---

### 5. `ValueError` from `backtesting.py` due to insufficient data

*   **Symptom:** Backtests failed with `ValueError: Indicators must return ... numpy.arrays of same length as 'data' ... returned value: None`.
*   **Root Cause:** The test data provided to the backtest was shorter than the period required by the longest indicator (e.g., 100 data points for a 200-period SMA). `pandas-ta` returns `None` in this case, which `backtesting.py` cannot handle.
*   **Resolution:** Increased the length of the sample data in the test fixtures to be longer than the longest indicator period (e.g., 250 data points).
*   **Learning:** When testing strategies with rolling indicators, ensure the test data is sufficiently long to cover the indicator's warm-up period.

---

### 6. `backtesting.py` data proxy object issue

*   **Symptom:** Even with sufficient data, `pandas-ta` indicators were returning `None` when called from within a `Strategy.init()` method.
*   **Root Cause:** `backtesting.py` passes a special data proxy object (`self.data.Close`) to the indicator function, not a standard pandas Series. `pandas-ta` does not seem to handle this proxy object correctly.
*   **Resolution:** Explicitly converted the data proxy to a pandas Series before passing it to the indicator function: `close_series = pd.Series(self.data.Close)`.
*   **Learning:** Be aware of how libraries pass data internally. Data proxies or custom objects can cause unexpected behavior with third-party libraries that expect standard types like pandas Series.

---

### 7. Miscellaneous Test Failures

*   **`AttributeError: 'Backtest' object has no attribute 'strategy'`:** The public attribute is `_strategy`, not `strategy`. The test was updated to use the private attribute.
*   **`NameError: name 'pd' is not defined`:** A missing `import pandas as pd` statement in `src/core/strategy.py`.
*   **`AssertionError: assert isinstance(<class '...'>, ...)`:** `bt._strategy` holds the strategy *class*, not an *instance* of the class. The assertion was changed to `assert bt._strategy is SmaCross`.

These highlight the importance of careful, iterative debugging.

---

### 8. Pydantic Model Validation with Default Values

*   **Symptom:** A test expecting a `ValueError` when loading an invalid JSON file into a Pydantic model was failing because no error was raised.
*   **Root Cause:** The Pydantic model (`RunState`) had fields with default values (e.g., `iteration_number: int = 0`). When `model_validate()` was called with a JSON object that was missing these fields, Pydantic did not raise a `ValidationError`. Instead, it silently created a model instance with the default values.
*   **Resolution:** Removed the default values from the model's fields (e.g., changed to `iteration_number: int`). This forced `model_validate()` to require the fields to be present in the source data, causing it to raise a `ValidationError` as expected when they were missing. The service layer was then updated to explicitly provide default values when creating a new, fresh instance.
*   **Learning:** When using Pydantic for strict data validation (e.g., loading a state file that is expected to conform to a schema), avoid using default values for top-level fields. This ensures that malformed or incomplete data results in a loud failure (`ValidationError`) rather than a silent creation of a default object, which could hide bugs or data corruption issues.

---

### 9. `ImportError` on `StrategyEngine` from `main.py`

*   **Symptom:** `python src/main.py` failed with `ImportError: cannot import name 'StrategyEngine' from 'services'`.
*   **Root Cause:** A new service, `StrategyEngine`, was created in `src/services/strategy_engine.py`, but the package's `__init__.py` file (`src/services/__init__.py`) was not updated to import and expose it in the `__all__` list.
*   **Resolution:** Added `from .strategy_engine import StrategyEngine` and included `"StrategyEngine"` in the `__all__` list in `src/services/__init__.py`.
*   **Learning:** Adherence to `H-6` and `H-7` is critical. Whenever a new public class is added to a module, the package's `__init__.py` must be updated to make it part of the public API.

---

### 10. `ValueError` in `yf.download` due to incorrect period format

---

### 11. Test Failures Due to Environment Inconsistencies

*   **Symptom:** The `pytest` suite failed with various `ModuleNotFoundError` and `ImportError` issues, specifically for `services`, `core`, `pkg_resources`, and `pyarrow`.
*   **Root Cause:** The test environment was not set up correctly. This was due to a combination of missing dependencies and the project not being installed in an editable mode.
*   **Resolution:**
    1.  Installed the project in editable mode: `pip install -e .`. This resolved the `services` and `core` import errors by making the `src` directory available on the Python path.
    2.  Installed `setuptools`: `pip install setuptools`. This resolved the `pkg_resources` error, which is a dependency of `pandas-ta`.
    3.  Installed `pyarrow`: `pip install pyarrow`. This resolved the `ImportError` for the parquet engine in pandas.
*   **Learning:** A robust development setup script or clear documentation is critical. When encountering import errors during testing, the first step should be to verify that the project is installed in editable mode and all dependencies from `requirements.txt` are installed.

*   **Symptom:** `main.py` failed with a `ValueError` from `yfinance`, stating that time data did not match the expected format.
*   **Root Cause:** A configuration value for `data_period` (e.g., "10y") was being passed to the `DataService.get_data` method, which in turn passed it to `yfinance.download`. However, the `DataService` is designed to accept `start_date` and `end_date` strings, not a period string.
*   **Resolution:** Removed the incorrect `config.app.data_period` argument from the `data_service.get_data(ticker)` call in `main.py`, allowing the method to use its robust default start and end date parameters.
*   **Learning:** Always verify the exact signature and expected arguments of a service method before calling it. Do not assume a configuration value's name maps directly to a function's parameter, especially when default values are provided.

---

### 12. Circular Import between `core` and `services`

*   **Symptom:** `python src/main.py` failed with `ImportError: cannot import name 'ConfigService' from partially initialized module 'services' (most likely due to a circular import)`.
*   **Root Cause:** The `Orchestrator` was located in `src/core`, but it needs to import and use classes from `src/services`. At the same time, `services` (specifically `ConfigService`) needed to import models from `src/core`. This created an import cycle (`main` -> `services` -> `core` -> `services`).
*   **Resolution:** The `Orchestrator` is not a "core" component in the sense of pure, offline logic; it's the top-level application coordinator. It was moved from `src/core/orchestrator.py` to `src/orchestrator.py`. All relevant imports in `main.py`, `core/__init__.py`, and tests were updated.
*   **Learning:** The `core` module should have no dependencies on any other application module (`services`, etc.). It should only contain self-contained data models and pure functions. Application logic that coordinates multiple services belongs at a higher level. This enforces the Acyclic Import Graph rule (H-12).

---

### 13. `TypeError` on Service Instantiation

*   **Symptom:** `main.py` failed with `TypeError: __init__() got an unexpected keyword argument`. This happened for multiple services (`StateManager`, `LLMService`).
*   **Root Cause:** The arguments being passed to the service's constructor in `main.py` did not match the arguments defined in the service's `__init__` method. For instance, `LLMService` was passed a `config` object it didn't need, as it configures itself from environment variables.
*   **Resolution:** For each case, the `__init__` method of the service was treated as the source of truth. The instantiation call in `main.py` was corrected to provide the exact arguments required. This also involved refactoring `StateManager` to handle per-ticker state files more robustly.
*   **Learning:** A mismatch between instantiation and definition is a common bug. It highlights the need for careful integration. When a service's dependencies change, all places where it is instantiated must be updated.

---

### 14. `StrategyEngine` Logical Flaws

*   **Symptom:** The application ran but backtests consistently failed inside the `StrategyEngine` with `TypeError` (missing arguments for indicators) or `NameError` (variable not defined).
*   **Root Cause:** The initial `StrategyEngine` was too simplistic and had two major flaws:
    1.  **It only passed `close` data to indicators:** It called every `pandas-ta` function with only the `close` series, but many indicators (`atr`, `kc`, etc.) require `high`, `low`, and `volume`.
    2.  **It did not handle multi-column indicators predictably:** For indicators like `bbands`, it created column names like `bbands_BBL_20_2_0`, which the LLM could not possibly guess. The LLM would logically try to use names like `bb_lower`.
*   **Resolution:** The `StrategyEngine` was significantly refactored:
    1.  It now uses Python's `inspect.signature` to determine which OHLCV columns an indicator function requires at runtime and dynamically provides only those arguments.
    2.  It now has a hard-coded mapping for common multi-column indicators (`bbands`, `kc`, `macd`) to create intuitive and predictable variable names (e.g., `bb_lower`, `macd_signal`) for the `asteval` context.
*   **Learning:** Systems that interpret generated code or configurations (even safe ones like this) must be robust. The interpreter (`StrategyEngine`) needs to be flexible enough to handle the variety of valid inputs, and the context provided to the generator (the LLM) must be clear and predictable.

---

### 15. `asteval` returning `None`

*   **Symptom:** `StrategyEngine` failed with `AttributeError: 'NoneType' object has no attribute 'astype'`.
*   **Root Cause:** If an `asteval` expression was valid but resulted in a `None` value (e.g., comparing `NaN` values), the subsequent `np.nan_to_num(...).astype(bool)` call would fail.
*   **Resolution:** Added a check after the `asteval.eval()` call. If the result is `None`, it is replaced with a boolean array of all `False` values, effectively treating it as "no signal".
*   **Learning:** Be defensive when handling the output of external libraries or evaluators. Always consider edge cases like `None` or other unexpected return types.
