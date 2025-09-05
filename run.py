#!/usr/bin/env python
import sys
from pathlib import Path
import io

# Ensure stdout/stderr can handle Unicode (utf-8) so logging of Unicode
# characters (like block characters used in histograms) doesn't raise
# UnicodeEncodeError on Windows consoles that use legacy codepages.
try:
    # Python 3.7+ supports reconfigure
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    # Fallback for older Python versions / unusual streams
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        # If reconfiguration fails, continue without raising; logging may still error
        pass

# Add the project root to the python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from praxis_engine.main import app

if __name__ == "__main__":
    app()
