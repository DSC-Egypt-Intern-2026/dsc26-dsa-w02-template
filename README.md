# W2 · Rawaj Pay transfers: a contract you can execute

DSC Summer Internship 2026 · Data Science & Analytics track · Task after session W2 (Data quality and data contracts)

**Repository name:** `dsc26-dsa-w02` (exactly this, public, in your own GitHub account)
**Language:** Python 3.12 · pandas 2.3.3 · pytest 9.1.1 (all versions pinned in `requirements.txt`)
**Expected time:** 2.5–3.5 hours

## Scenario

Rawaj Pay's software pod sends the data pod a daily transfers extract as CSV. Last week the AI pod trained on an extract with duplicated rows and planted amounts like "1,250.00", and nobody noticed for two days. Dina wants it to never happen again. The data contract has been agreed and is in `contracts/transfers_v1.json`. You write the code that enforces it: it validates an extract against **any** contract in that format, splits it into clean and quarantined rows, profiles it, and flags outliers for the fraud analysts.

The hidden tests run your code against other extracts and also against a different contract, so nothing about the Rawaj columns may be hard-coded.

## Set up

```bash
uv venv --python 3.12
source .venv/bin/activate            # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt   # the pinned versions; do not add packages
pytest -q                            # public tests: they fail until you build the task
```

You cannot add packages. The grader has exactly the packages in `requirements.txt` and no network. Pandera and Great Expectations are not installed; write the checker yourself.

## Files

```
rawaj_dq/
  io.py            read_raw(path): reads every cell as text. Provided by DSC. Do not change (the grader overwrites it).
  contract.py      load_contract(path): checks the contract's structure, lower-cases null_tokens. Do not change.
  validate.py      YOU WRITE: check_schema, validate, conform, profile, quality_report
  outliers.py      YOU WRITE: flag_outliers
contracts/transfers_v1.json   the agreed contract. Do not change (the grader overwrites it).
data/transfers_sample.csv     2,040 synthetic transfers with planted problems of every kind
tests/test_public.py          public tests
AI_USAGE.md                   fill in before you submit (see the end of this file)
```

You may add your own helper modules inside `rawaj_dq/` and your own tests under `tests/`. Notebooks are welcome for exploring, but the grader imports only your `.py` files.

## The contract format

```json
{
  "name": "rawaj.transfers",
  "version": "1.0.0",
  "null_tokens": ["", "na", "n/a", "null", "none", "-"],
  "primary_key": "transfer_id",
  "columns": {
    "transfer_id":      {"type": "string",    "nullable": false, "pattern": "^TRF-[0-9]{8}$"},
    "created_at":       {"type": "timestamp", "nullable": false, "not_after_as_of": true},
    "sender_account":   {"type": "string",    "nullable": false, "pattern": "^[0-9]{10}$"},
    "receiver_account": {"type": "string",    "nullable": false, "pattern": "^[0-9]{10}$"},
    "amount":           {"type": "money",     "nullable": false, "min": 100, "max": 6000000},
    "channel":          {"type": "string",    "nullable": false, "allowed": ["app", "ussd", "web", "agent"]},
    "status":           {"type": "string",    "nullable": false, "allowed": ["completed", "reversed", "failed"]},
    "is_first_payee":   {"type": "boolean",   "nullable": true},
    "device_age_days":  {"type": "integer",   "nullable": true, "min": 0}
  },
  "row_rules": [
    {"rule": "distinct", "columns": ["sender_account", "receiver_account"]}
  ]
}
```

Other contracts in this format can have any column names, any of the five types, their own `null_tokens`, patterns, ranges and allowed values, and an empty `row_rules`.

## The rules your code must apply

- **Headers** are matched after stripping spaces and lower-casing (`" Amount "` is `amount`). Every column in the contract is required; extra columns are allowed.
- **Cells** are stripped of surrounding whitespace before any check. A cell is **null** if its stripped, lower-cased value is in `null_tokens`. A null in a column with `"nullable": false` is a `not_null` violation; a null in a nullable column is fine. No other check runs on a null cell.
- **Types** (a cell that fails its type gets a `type` violation, and no further checks):
  - `string`: anything.
  - `integer`: optional sign then digits only (`"+7"` yes, `"12.0"` no).
  - `money`: EGP, optional leading `-`, digits, optionally a point and one or two digits. No thousands separators, no exponent. Conformed to **integer piastres**, exactly (`"0.29"` → 29, `"12.5"` → 1250).
  - `boolean`: `true`, `false`, `1`, `0`, `yes`, `no`, any case.
  - `timestamp`: ISO 8601 with a date, a time and an offset (`Z`, `+03:00` or `+0300`). No offset, or a date only, is a `type` violation. Conformed to UTC.
- **Domain checks** on valid, non-null cells: `pattern` is a full match on the stripped value, case-sensitive (`pattern` violation); `allowed` compares lower-cased values, and conformed values are lower-cased (`allowed` violation); `min` and `max` apply to integers and to money **in piastres** (`min`, `max` violations); a timestamp column with `not_after_as_of` must not be later than `as_of` (`future` violation). A timestamp exactly equal to `as_of` is not in the future.
- **Keys.** Among rows whose primary key is not null, compare stripped raw values of all contract columns (rows are grouped by the stripped key). If every row sharing a key is identical, the first is kept and each later copy gets a `duplicate` violation with severity `warning`; copies are dropped from the clean output and are not quarantined. If rows share a key but differ anywhere, **every** row with that key gets `conflicting_key` (error). Key violations are reported on the primary-key column, with the key cell as `value`.
- **Row rule `distinct`**: when both columns are non-null and their stripped values are equal, the row gets a `distinct` violation reported on the first column.
- Every violation except `duplicate` has severity `error`. A row with any error is quarantined.
- **A later exact copy of a row that has an error** (for example, the same row with amount `"abc"` exported twice) still gets its `duplicate` warning, but because it has an error itself it is quarantined like any other row with an error. So in `quality_report` it counts as quarantined, not as a dropped copy: every row is counted exactly once, and `rows_in = rows_clean + rows_quarantined + rows_dropped_duplicates` always holds.

## What to build

`rawaj_dq/validate.py`:

```python
import pandas as pd

VIOLATION_COLUMNS = ["row", "column", "rule", "severity", "value"]

class SchemaError(Exception): ...

def check_schema(raw: pd.DataFrame, contract: dict) -> list[str]:
    """Messages like 'missing column: amount' and 'unexpected column: note'. Never raises."""

def validate(raw: pd.DataFrame, contract: dict, as_of: pd.Timestamp) -> pd.DataFrame:
    """One row per violation, columns VIOLATION_COLUMNS, sorted by row, column, rule, index 0..n-1.
    row: 0-based position in raw; value: the raw cell as it arrived (the key value for key rules).
    Raises SchemaError if a contract column is missing, ValueError if as_of has no time zone."""

def conform(raw: pd.DataFrame, contract: dict, as_of: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(clean, quarantine). clean: rows with no error and not a dropped copy, contract columns only,
    typed: string -> "string", integer and money -> "Int64", boolean -> "boolean",
    timestamp -> datetime64[ns, UTC]. quarantine: the raw rows with an error, as they arrived,
    plus a 'reasons' column: the distinct error rules for that row, sorted, joined with ';'.
    Both keep the original row positions as their index."""

def profile(raw: pd.DataFrame, contract: dict) -> pd.DataFrame:
    """Index: contract columns. Columns: null_count, null_rate (0..1), n_unique (distinct stripped non-null values)."""

def quality_report(raw: pd.DataFrame, contract: dict, as_of: pd.Timestamp) -> dict:
    """{'contract_version', 'rows_in', 'rows_clean', 'rows_quarantined', 'rows_dropped_duplicates',
        'errors_by_rule': {rule: number of error violations}}"""
```

`rawaj_dq/outliers.py`:

```python
def flag_outliers(values: pd.Series, groups: pd.Series | None = None,
                  threshold: float = 3.5, min_group_size: int = 5) -> pd.Series:
    """Boolean Series, same index as values. Modified z-score 0.6745 * (x - median) / MAD within each group;
    flag |z| > threshold. Missing values and rows with a missing group are never flagged.
    A group with fewer than min_group_size non-missing values, or with MAD == 0, gets no flags."""
```

Details the hidden tests rely on (read these twice):

- `validate` sorts by `row`, then `column` name, then `rule` name, in plain string order, and resets the index to 0..n-1. `row` is the 0-based position in `raw`, whatever index `raw` has.
- `as_of` is checked first: a naive `as_of` raises `ValueError`. A missing contract column raises `SchemaError` from `validate`, `conform` and `quality_report`. `check_schema` only returns messages, in the formats `missing column: <name>` and `unexpected column: <name>` (names as normalised headers).
- `clean` has exactly the contract columns, in contract order. String values are stripped; values in a column with `allowed` are lower-cased. Integer and money columns are `"Int64"` (money in piastres), booleans `"boolean"`, timestamps `datetime64[ns, UTC]`. Nulls in nullable columns become `<NA>`/`NaT`.
- `quarantine` keeps all columns of `raw` (headers normalised: stripped, lower-cased) with every cell exactly as it arrived, plus `reasons`, e.g. `"allowed;type"`. Only error rules appear in `reasons`.
- `profile` counts per contract column: `null_count` (cells that are null tokens), `null_rate` = null_count / rows (0.0 for an empty frame), `n_unique` = number of distinct **stripped, non-null values, case-sensitive** (`"App"` and `"app"` are two values; this is the profile of what arrived, before conforming).
- `quality_report["errors_by_rule"]` counts error violations per rule (a rule with no errors may be left out). `contract_version` is the contract's `version`.
- `flag_outliers` returns dtype `bool` (NumPy `bool`, not the nullable `"boolean"`), with exactly the index of `values`. `values` may contain `NaN`/`<NA>`; `groups` may be `None` (one group) or contain missing values.

## Public tests

`tests/test_public.py` has six tests. Run them with `pytest -q` from the repository root. They fail on the starter (with `NotImplementedError`) and pass on a correct solution. Passing them is necessary, not sufficient: write your own tests for the edge cases above.

## How grading works

1. Push to `dsc26-dsa-w02`, then press **Submit for grading** on DSC Hex. The grader pins your latest commit and clones it.
2. If `AI_USAGE.md` is missing or lacks any of its three headings, the grader stops and reports **0**.
3. DSC's copies of `rawaj_dq/io.py`, `rawaj_dq/contract.py` and `contracts/transfers_v1.json` replace yours. Any `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg` or `[tool.pytest]` settings at the repository root are removed.
4. The hidden tests run with `pytest` on Python 3.12 with the pinned packages, network off, 60 s per test and 3 minutes for the whole run. They generate **different seeded extracts** from the sample (same structure, different rows, different planted problems), use a contract you have not seen, and use Hypothesis to throw hundreds of random amounts at your money parser.
5. You get a score from 0 to 100 and, per hidden test, its public name, pass or fail, and a short hint. A test ID passes only if every case under it passes. You never see the hidden test code.
6. You get 5 grader runs per day. Run the public tests locally first; the grader is a judge, not a debugger.

| ID | Public name | What it checks | Weight |
|---|---|---|---|
| H01 | schema: missing column stops, messy headers and extra columns don't | `SchemaError` on a missing column; headers like `"  AMOUNT "` accepted; an extra column produces no violation and appears in `check_schema` | 6 |
| H02 | nulls: every null token, any case, with spaces | Eight spellings in a non-nullable and two nullable columns: exactly one `not_null`, nothing else | 8 |
| H03 | types: integer, money and boolean formats | Ten cases including `"1,250.00"`, `"12.345"`, `"1e3"`, `"12.0"`, `"+7"`, `"Yes"`, `"maybe"` | 8 |
| H04 | money: exact to the piastre | 300 random amounts written with two, one or no decimals; conformed value equals the integer piastres | 8 |
| H05 | timestamps: offsets, DST night, naive rejected | `+03:00` and `+02:00` on 29 October 23:30, `Z`, `+0200` all land on the right UTC instant with a UTC dtype; naive and date-only values are `type` violations | 8 |
| H06 | freshness: later than as_of is future; naive as_of raises | One minute either side of `as_of`; `ValueError` for a naive `as_of` | 5 |
| H07 | pattern and allowed: case rules and leading zeros | Short account numbers and lower-case ids fail `pattern`; `" USSD "` passes `allowed` and conforms to `"ussd"` | 7 |
| H08 | duplicates: exact copies warned, conflicting keys quarantined | A key seen three times identically and a key with two different rows; warnings on the later copies only, errors on every conflicting row, correct clean and quarantine indexes | 10 |
| H09 | row rule: sender is not receiver | Equal values, including equal after stripping | 4 |
| H10 | conform: dtypes, indexes and reasons | Original positions kept; `reasons` is `"allowed;type"` for a row with both; nullable dtypes as specified | 8 |
| H11 | another contract: nothing hard-coded | A stock-count contract with different columns, null tokens, patterns, ranges and allowed values; the exact set of violations and conformed values | 10 |
| H12 | profile: null counts, rates and distinct values | A small frame where the answers are known | 6 |
| H13 | outliers: groups, MAD of zero, small groups, missing values, index | Per-group flags, nothing flagged when MAD is 0 or the group is too small, missing values and groups, index preserved, dtype `bool` | 8 |
| H14 | report: every row accounted for | Three seeded extracts and a copy of a bad row: `rows_in` = clean + quarantined + dropped copies, version passed through, conflicting keys counted | 4 |
| | | **Total** | **100** |

Late policy: ×1.0 within 72 hours of the session starting, ×0.6 for the following 7 days, ×0.5 after that until Thu 3 Dec 23:59. W5 reopens W2 at ×1.0. Your best attempt counts.

**On the sample.** `data/transfers_sample.csv` (2,040 rows) produces 1,884 clean rows, 137 quarantined rows and 19 dropped copies with the sample `as_of` of `2026-10-16T00:00:00Z`. One of the 20 exported copies in the sample is a copy of a row with an error, so it is quarantined, not dropped. The hidden extracts produce different numbers.

## AI_USAGE.md

AI tools are allowed. Keep the three headings `## Tools`, `## What AI got wrong` and `## In my own words`. The grader does not score the content, but it reports 0 if the file or a heading is missing. Under `## In my own words`, answer in one or two sentences each, without AI:

1. Why is a row with the same `transfer_id` but a different amount quarantined, while an exact copy is not?
2. Name one outlier in the sample extract you would show Dina rather than delete, and say why.

An assistant will get you a first draft quickly; the edge cases in this README decide the score.
