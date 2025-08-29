"""
Utility functions for calculating guard scores.
"""

def linear_score(value: float, min_val: float, max_val: float) -> float:
    """
    Calculates a linear score between 0.0 and 1.0.

    If min_val < max_val:
        - score is 1.0 if value >= max_val
        - score is 0.0 if value <= min_val
    If min_val > max_val:
        - score is 1.0 if value <= max_val
        - score is 0.0 if value >= min_val

    The score is clamped between 0.0 and 1.0.
    """
    if min_val == max_val:
        return 1.0 if value >= min_val else 0.0

    # Handle inverse scoring (lower is better)
    if min_val > max_val:
        min_val, max_val = max_val, min_val
        score = 1.0 - ((value - min_val) / (max_val - min_val))
    else:
        score = (value - min_val) / (max_val - min_val)

    return max(0.0, min(1.0, score))
