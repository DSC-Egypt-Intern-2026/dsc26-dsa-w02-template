"""Provided by DSC. Do not change: the grader overwrites this file."""
import json
from pathlib import Path

TYPES = {"string", "integer", "money", "timestamp", "boolean"}
COLUMN_KEYS = {"type", "nullable", "pattern", "allowed", "min", "max", "not_after_as_of"}


class ContractError(ValueError):
    pass


def load_contract(path: str | Path) -> dict:
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    for name, spec in contract["columns"].items():
        if spec.get("type") not in TYPES:
            raise ContractError(f"{name}: unknown type {spec.get('type')!r}")
        unknown = set(spec) - COLUMN_KEYS
        if unknown:
            raise ContractError(f"{name}: unknown keys {sorted(unknown)}")
    if contract["primary_key"] not in contract["columns"]:
        raise ContractError("primary_key must be one of the columns")
    contract["null_tokens"] = [t.strip().lower() for t in contract.get("null_tokens", [""])]
    contract.setdefault("row_rules", [])
    return contract
