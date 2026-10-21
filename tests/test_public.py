import io

import pandas as pd
import pytest

from rawaj_dq.contract import load_contract
from rawaj_dq.io import read_raw
from rawaj_dq.outliers import flag_outliers
from rawaj_dq.validate import SchemaError, conform, validate

CONTRACT = load_contract("contracts/transfers_v1.json")
AS_OF = pd.Timestamp("2026-10-16T00:00:00Z")
HEADER = "transfer_id,created_at,sender_account,receiver_account,amount,channel,status,is_first_payee,device_age_days\n"
GOOD = "TRF-00000001,2026-10-14T23:30:00+03:00,0012345678,0098765432,1250.50,app,completed,false,12\n"


def raw(*rows: str) -> pd.DataFrame:
    return read_raw(io.StringIO(HEADER + "".join(rows)))


def rules(v: pd.DataFrame) -> set[tuple[int, str, str]]:
    return set(zip(v["row"], v["column"], v["rule"]))


def test_clean_row_has_no_violations_and_is_typed():
    clean, quarantine = conform(raw(GOOD), CONTRACT, AS_OF)
    assert len(quarantine) == 0
    row = clean.iloc[0]
    assert row["sender_account"] == "0012345678"            # leading zeros kept
    assert row["amount"] == 125050                          # piastres, exact
    assert row["created_at"] == pd.Timestamp("2026-10-14T20:30:00Z")


def test_null_tokens_and_types():
    bad = "TRF-00000002,2026-10-14T10:00:00+03:00,0012345678,0098765432, N/A ,APP ,completed,maybe,\n"
    v = validate(raw(GOOD, bad), CONTRACT, AS_OF)
    assert (1, "amount", "not_null") in rules(v)
    assert (1, "is_first_payee", "type") in rules(v)
    assert (1, "channel", "allowed") not in rules(v)        # case and spaces are not errors
    assert (1, "device_age_days", "not_null") not in rules(v)  # nullable


def test_naive_timestamp_is_a_type_error():
    naive = GOOD.replace("TRF-00000001", "TRF-00000003").replace("+03:00", "")
    v = validate(raw(naive), CONTRACT, AS_OF)
    assert (0, "created_at", "type") in rules(v)


def test_exact_duplicate_is_a_warning_and_first_copy_kept():
    clean, quarantine = conform(raw(GOOD, GOOD), CONTRACT, AS_OF)
    assert list(clean.index) == [0] and len(quarantine) == 0
    v = validate(raw(GOOD, GOOD), CONTRACT, AS_OF)
    assert v.loc[v["rule"] == "duplicate", "severity"].tolist() == ["warning"]


def test_missing_column_raises():
    with pytest.raises(SchemaError):
        validate(read_raw(io.StringIO("transfer_id,amount\nTRF-00000001,10\n")), CONTRACT, AS_OF)


def test_outlier_flags_the_obvious_one():
    s = pd.Series([100, 102, 98, 101, 99, 103, 97, 5000])
    assert flag_outliers(s).tolist() == [False] * 7 + [True]
