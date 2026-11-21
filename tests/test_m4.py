from app.modules.m4_paths.rules import evaluate
from app.pipeline import calculate
def scan(id,node,at):return {"scan_id":str(id),"parcel":"01","node":node,"event_utc":at,"received_utc":"2026-11-09T00:00:00Z","zone":"Asia/Tokyo","destination":"JP","promised_hours":"24","declared_value":"200","reported":"0","_sources":[id]}
def test_real_eight_parcels(result): assert result["stages"][3]["metrics"]["parcels"]==8
def test_real_regression_isolated(result): assert result["stages"][3]["quarantine"][0]["reason"]=="PATH_REGRESSION"
def test_late_upload_event_time_decides():
    "TRAP-13"
    r=evaluate([scan(2,"DELIVERED","2026-11-04T00:00:00Z"),scan(1,"ACCEPT","2026-11-02T00:00:00Z")],{})["rows"][0]
    assert r["delivered_at"]=="2026-11-04T00:00:00Z" and r["scan_count"]==2
def test_missing_accept(): assert evaluate([scan(1,"DELIVERED","2026-11-04T00:00:00Z")],{})["quarantine"][0]["reason"]=="MISSING_ACCEPT"
def test_order_independent():
    rows=[scan(1,"ACCEPT","2026-11-02T00:00:00Z"),scan(2,"DELIVERED","2026-11-04T00:00:00Z")];assert evaluate(rows,{})==evaluate(list(reversed(rows)),{})
def test_simultaneous_conflict():
    r=evaluate([scan(1,"ACCEPT","2026-11-02T00:00:00Z"),scan(2,"DEPART","2026-11-02T00:00:00Z")],{});assert r["quarantine"][0]["reason"]=="SIMULTANEOUS_CONFLICT"
def test_real_group_lineage(result): assert all(len(r["_sources"])==4 for r in result["stages"][3]["rows"])
