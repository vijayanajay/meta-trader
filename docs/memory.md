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
This is a pragmatic workaround for a broken dependency when direct modification is not possible. It's clearly marked as a hack and should be removed if `pandas-ta` is updated. This highlights the fragility of relying on unpinned or older dependencies.

---
