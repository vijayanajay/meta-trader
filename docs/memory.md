# Memory Log

This document records issues, their resolutions, and key learnings from the development process to prevent repeating mistakes.

---

### 1. `pandas-ta` Dependency Issue

**Date:** 2025-08-20

**Issue:**
During testing, an `ImportError: cannot import name 'NaN' from 'numpy'` was raised from within the `pandas-ta` library. Investigation revealed that the version of `pandas-ta` being used relies on the deprecated `numpy.NaN` alias, which has been removed in recent `numpy` versions.

**Resolution:**
The tools available do not allow modifying files outside the project repository (e.g., in `site-packages`). The chosen solution was to apply a monkey-patch in our own code before the `pandas-ta` import.

In `self_improving_quant/core/strategy.py`, the following lines were added:
```python
# HACK: Monkey-patch numpy for a bug in an old version of pandas-ta
import numpy
if not hasattr(numpy, "NaN"):
    numpy.NaN = numpy.nan
import pandas_ta as ta
```

**Learning:**
This is a pragmatic workaround for a broken dependency when direct modification is not possible. It's clearly marked as a hack and should be removed if `pandas-ta` is updated. This highlights the fragility of relying on unpinned or older dependencies. **Note:** This issue was later resolved by pinning `numpy<2.0.0` in `requirements.txt`.

---

### 2. Environment Mismatch and `pkg_resources` Error

**Date:** 2025-08-20

**Issue:**
After setting up a new environment with `pip install pandas pandas-ta ...`, the test suite failed to collect tests with two different errors:
1. `ModuleNotFoundError: No module named 'pkg_resources'`
2. `ImportError: cannot import name 'NaN' from 'numpy'`

The second error was particularly confusing, as it was the same issue that a previous `numpy` monkey-patch was supposed to solve.

**Resolution:**
The root cause was a mismatch between the environment created by `pip install ...` (which fetches the latest versions) and the specific, pinned versions required by the project.
1. The `pkg_resources` error was solved by installing `setuptools`, which was missing from the initial install but present in `requirements.txt`.
2. The `numpy.NaN` error was solved by discovering that `requirements.txt` pins `numpy<2.0.0`. The initial install had fetched `numpy>=2.0.0`, which had removed `numpy.NaN`.

The final, correct resolution was to discard the environment and rebuild it using the command `pip install -r requirements.txt`. This installed the correct, pinned versions of all dependencies and resolved all test errors.

**Learning:**
Always use the pinned `requirements.txt` file to create a development environment. Do not install packages individually, as this can lead to dependency conflicts that have already been solved. The command `pip install -r requirements.txt` is the canonical way to ensure a reproducible environment.
