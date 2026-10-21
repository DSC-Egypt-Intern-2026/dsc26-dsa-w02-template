"""W2: flag outliers for a human to review. Implement flag_outliers; do not change its signature."""
import pandas as pd


def flag_outliers(values: pd.Series, groups: pd.Series | None = None,
                  threshold: float = 3.5, min_group_size: int = 5) -> pd.Series:
    """Boolean Series, same index as values. Modified z-score 0.6745 * (x - median) / MAD within each group;
    flag |z| > threshold. Missing values and rows with a missing group are never flagged.
    A group with fewer than min_group_size non-missing values, or with MAD == 0, gets no flags."""
    raise NotImplementedError
