import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from self_improving_quant.utils.retry import retry_on_failure

# Configure logger for testing
logging.basicConfig(level=logging.INFO)


class MyTestException(Exception):
    """Custom exception for testing."""

    pass


def test_retry_succeeds_on_first_try():
    """Test that the decorator calls the function once if it succeeds."""
    mock_func = MagicMock(__name__="mock_func")
    mock_func.return_value = "success"

    decorated_func = retry_on_failure(retries=3, delay=0.1)(mock_func)
    result = decorated_func()

    assert result == "success"
    mock_func.assert_called_once()


@patch("time.sleep", return_value=None)
def test_retry_succeeds_after_failures(mock_sleep):
    """Test that the decorator retries on failure and eventually succeeds."""
    mock_func = MagicMock(__name__="mock_func")
    mock_func.side_effect = [MyTestException("fail"), MyTestException("fail"), "success"]

    decorated_func = retry_on_failure(retries=3, delay=0.1, exceptions=(MyTestException,))(mock_func)
    result = decorated_func()

    assert result == "success"
    assert mock_func.call_count == 3
    assert mock_sleep.call_count == 2


@patch("time.sleep", return_value=None)
def test_retry_fails_after_all_retries(mock_sleep):
    """Test that the decorator raises an exception after all retries are exhausted."""
    mock_func = MagicMock(__name__="mock_func")
    mock_func.side_effect = MyTestException("permanent failure")

    decorated_func = retry_on_failure(retries=3, delay=0.1, exceptions=(MyTestException,))(mock_func)

    with pytest.raises(MyTestException) as excinfo:
        decorated_func()

    assert "permanent failure" in str(excinfo.value)
    assert mock_func.call_count == 3
    assert mock_sleep.call_count == 2


def test_retry_ignores_other_exceptions():
    """Test that the decorator does not catch exceptions not in the specified list."""
    mock_func = MagicMock(__name__="mock_func")
    mock_func.side_effect = ValueError("wrong exception")

    decorated_func = retry_on_failure(retries=3, delay=0.1, exceptions=(MyTestException,))(mock_func)

    with pytest.raises(ValueError):
        decorated_func()

    mock_func.assert_called_once()
