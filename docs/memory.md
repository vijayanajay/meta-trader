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
