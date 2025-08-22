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
