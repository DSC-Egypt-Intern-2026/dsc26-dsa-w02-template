"""Provided by DSC. Do not change: the grader overwrites this file."""
from pathlib import Path

import pandas as pd


def read_raw(path: str | Path) -> pd.DataFrame:
    """Read a CSV extract exactly as it is: every cell a str, nothing turned into NaN."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
