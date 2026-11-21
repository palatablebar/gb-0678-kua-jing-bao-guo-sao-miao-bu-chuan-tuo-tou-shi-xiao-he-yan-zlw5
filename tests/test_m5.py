from app.modules.m5_timeliness.rules import working_hours,evaluate
from app.values import instant
from decimal import Decimal
import pytest
from app.errors import DomainError
def test_real_holiday_excluded(result): assert result["stages"][4]["rows"][0]["working_hours"]=="24.0"
def test_real_sla_uses_event_not_upload(result): assert result["stages"][4]["metrics"]["compensation"]=="0.00"
def test_holiday_full_day_stops():
    "TRAP-23"
    assert working_hours(instant("2026-11-02T15:00:00Z"),instant("2026-11-03T15:00:00Z"),"Asia/Tokyo",{"2026-11-03"})==0
def test_weekend_stops(): assert working_hours(instant("2026-11-06T15:00:00Z"),instant("2026-11-08T15:00:00Z"),"Asia/Tokyo",set())==0
def test_reversed_interval_rejected():
    with pytest.raises(DomainError):working_hours(instant("2026-11-04T00:00:00Z"),instant("2026-11-02T00:00:00Z"),"Asia/Tokyo",set())
def test_compensation_capped():
    row={"accepted_at":"2026-11-02T00:00:00Z","delivered_at":"2026-11-06T00:00:00Z","zone":"Asia/Tokyo","destination":"JP","promised_hours":"0","declared_value":"100"}
    assert evaluate([row],{})["rows"][0]["expected"]=="10.00"
def test_dst_actual_elapsed_hours():
    "TRAP-12"
    assert working_hours(instant("2026-11-01T04:00:00Z"),instant("2026-11-02T05:00:00Z"),"America/New_York",set())==0
