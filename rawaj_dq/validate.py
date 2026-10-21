"""W2: validate a CSV extract against a data contract. Implement every function below.

Read README.md for the exact rules. Do not change the names or signatures: the hidden tests import them.
"""
import pandas as pd

VIOLATION_COLUMNS = ["row", "column", "rule", "severity", "value"]


class SchemaError(Exception):
    """Raised by validate/conform/quality_report when a contract column is missing from the extract."""


def check_schema(raw: pd.DataFrame, contract: dict) -> list[str]:
    """Messages like 'missing column: amount' and 'unexpected column: note'. Never raises."""
    raise NotImplementedError


def validate(raw: pd.DataFrame, contract: dict, as_of: pd.Timestamp) -> pd.DataFrame:
    """One row per violation, columns VIOLATION_COLUMNS, sorted by row, column, rule, index 0..n-1.
    row: 0-based position in raw; value: the raw cell as it arrived (the key value for key rules).
    Raises SchemaError if a contract column is missing, ValueError if as_of has no time zone."""
    raise NotImplementedError


def conform(raw: pd.DataFrame, contract: dict, as_of: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(clean, quarantine). clean: rows with no error and not a dropped copy, contract columns only,
    typed: string -> "string", integer and money -> "Int64", boolean -> "boolean",
    timestamp -> datetime64[ns, UTC]. quarantine: the raw rows with an error, as they arrived,
    plus a 'reasons' column: the distinct error rules for that row, sorted, joined with ';'.
    Both keep the original row positions as their index."""
    raise NotImplementedError


def profile(raw: pd.DataFrame, contract: dict) -> pd.DataFrame:
    """Index: contract columns. Columns: null_count, null_rate (0..1), n_unique (distinct stripped non-null values)."""
    raise NotImplementedError


def quality_report(raw: pd.DataFrame, contract: dict, as_of: pd.Timestamp) -> dict:
    """{'contract_version', 'rows_in', 'rows_clean', 'rows_quarantined', 'rows_dropped_duplicates',
        'errors_by_rule': {rule: number of error violations}}"""
    raise NotImplementedError
