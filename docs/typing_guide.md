# Typing Guide for the Self-Improving Quant Engine

This project enforces strict static typing using `mypy --strict`. This guide explains how to work within this environment, especially when dealing with third-party libraries that may not be fully typed. Adhering to these standards is mandatory (H-1).

## `mypy` Configuration

Our `mypy` configuration is defined in `pyproject.toml`. The `strict = true` flag enables all strictness checks. However, some of our key dependencies do not provide complete type stubs, which would cause `mypy` to fail. To handle this, we use `overrides` to selectively relax the rules for these specific libraries:

```toml
[tool.mypy]
python_version = "3.12"
packages = ["src", "tests"]
strict = true

[[tool.mypy.overrides]]
module = "backtesting"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "backtesting.lib"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "pandas_ta"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "yfinance"
ignore_missing_imports = true
```

The `ignore_missing_imports = true` directive tells `mypy` not to complain if it cannot find type information for these modules. This is a pragmatic compromise that allows us to maintain a high level of type safety in our own code while still using these essential libraries.

## Handling Untyped Code

Even with the overrides, you will encounter situations where you interact with an untyped part of a library. Here are the approved patterns for handling these cases.

### Using `typing.cast` for Untyped Return Values

When you call a function from a library that `mypy` treats as untyped, the return value will have the type `Any`. To maintain type safety, you must immediately cast this value to the type you expect.

**Example:**

A function from a library might return a dictionary, but `mypy` doesn't know this.

```python
from typing import Any, cast

# Assume this function comes from an untyped library
def get_untyped_data() -> Any:
    return {"key": "value", "count": 5}

# Incorrect: 'raw_data' is Any, so mypy can't check its usage
raw_data = get_untyped_data()
# mypy would allow this, which could lead to a runtime error:
# print(raw_data["non_existent_key"])

# Correct: Use cast to inform mypy of the expected type
typed_data = cast(dict[str, Any], get_untyped_data())
# Now mypy can reason about the type:
print(typed_data["key"]) # OK
# And it will correctly flag potential errors:
# print(typed_data[0]) # Error: dict key must be a string
```

This pattern makes our code more robust by re-introducing type information at the boundary between our code and the untyped library.

### Using `# type: ignore[misc]` for Untyped Base Classes

The `backtesting.py` library's `Strategy` class is not defined in a way that `mypy` can easily understand for subclassing in `--strict` mode. When we define our own strategy class that inherits from it, `mypy` will raise a `[misc]` error.

In this specific, well-understood case, it is acceptable to suppress the error using a `# type: ignore[misc]` comment on the class definition line.

**Example (from `src/core/strategy.py`):**

```python
from backtesting import Strategy
# We know that subclassing the untyped 'Strategy' is safe here,
# so we ignore the specific error mypy would raise in strict mode.
class SmaCross(Strategy): # type: ignore[misc]
    def init(self) -> None:
        ...
    def next(self) -> None:
        ...
```

**This should be used sparingly.** It is only for cases where a library's design fundamentally conflicts with `mypy`'s strictness, and we have verified that the usage is correct. It should not be used to hide genuine type errors in our own code.
