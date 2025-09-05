import logging
import sys
from pathlib import Path
import io


class UTF8ConsoleHandler(logging.Handler):
    """Logging handler that writes UTF-8 encoded bytes directly to stdout.buffer.

    This avoids Python attempting to encode text using the system locale
    (cp1252 on Windows) which can raise UnicodeEncodeError for characters
    like U+2588. Falls back to a text stream if buffer isn't available.
    """

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self._stream = None

    def _ensure_stream(self):
        if self._stream is not None:
            return
        try:
            buf = sys.stdout.buffer
            # Keep a reference to the buffer; we'll write bytes directly.
            self._stream = buf
        except Exception:
            # Fallback to text stream with replace errors
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                self._stream = sys.stdout
            except Exception:
                self._stream = sys.stdout

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._ensure_stream()
            msg = self.format(record)
            if hasattr(self._stream, "write") and isinstance(self._stream, (io.BufferedWriter, io.RawIOBase)):
                # stream is a buffer -> write bytes
                try:
                    data = (msg + self.terminator).encode("utf-8", errors="replace")
                    self._stream.write(data)
                    try:
                        self._stream.flush()
                    except Exception:
                        pass
                    return
                except Exception:
                    # fallback to text write
                    pass

            # Otherwise write to text stream
            try:
                self._stream.write(msg + self.terminator)
                try:
                    self._stream.flush()
                except Exception:
                    pass
            except Exception:
                # Last resort: emit to default stderr
                try:
                    sys.stderr.write(msg + self.terminator)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)


def setup_file_logger(log_dir: str = "results", file_name: str = "backtest_results.log") -> None:
    """
    Configures the root logger with handlers for file and console output.
    This should be called once when the application starts.
    """
    root_logger = logging.getLogger()
    # Set the lowest level on the root logger to capture all messages
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers to prevent duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # File Handler for detailed logs
    results_dir = Path(log_dir)
    results_dir.mkdir(exist_ok=True)
    # Use explicit UTF-8 encoding for file logs to avoid locale-related
    # UnicodeEncodeError when writing Unicode characters.
    try:
        file_handler = logging.FileHandler(results_dir / file_name, mode='w', encoding='utf-8')
    except TypeError:
        # Older Python versions may not accept encoding arg; fall back to default
        file_handler = logging.FileHandler(results_dir / file_name, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console Handler for progress and summaries
    console_handler = UTF8ConsoleHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger instance for the given name.
    The logger is configured by the setup_file_logger function.
    """
    return logging.getLogger(name)
