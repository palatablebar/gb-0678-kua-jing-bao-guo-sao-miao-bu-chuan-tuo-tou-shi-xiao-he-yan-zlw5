from app.modules.m3_timezones.rules import evaluate
from app.values import instant,number
from decimal import Decimal
def test_real_late_uploads(result): assert result["stages"][2]["metrics"]["late_uploads"]==8
def test_real_naive_time_quarantine(result): assert any(r["reason"]=="INVALID_TIME" for r in result["stages"][2]["quarantine"])
def test_real_sentinel_not_zero(result):
    "TRAP-07"
    assert any(r["reason"]=="EMPTY_VALUE" for r in result["stages"][2]["quarantine"])
def test_equivalent_timezone():
    "TRAP-11"
    assert instant("2026-11-02T09:00:00+09:00")==instant("2026-11-02T00:00:00Z")
def test_received_before_event():
    r=evaluate([{"event_time":"2026-11-02T00:00:00Z","received_time":"2026-11-01T23:00:00Z","promised_hours":"24","declared_value":"2","reported":"0"}],{})
    assert r["quarantine"][0]["reason"]=="RECEIVED_BEFORE_EVENT"
def test_numeric_normalization():
    "TRAP-06"
    assert number("１,２００")==Decimal(1200)
def test_real_event_timestamp_kept(result): assert result["stages"][2]["rows"][3]["event_utc"]=="2026-11-04T00:00:00+00:00"
