import pytest
from app.pipeline import load_sample,calculate
from app.modules.m1_scans.rules import evaluate,event_uid
from app.config import COLUMNS
from app.errors import DomainError

HEADER=",".join(COLUMNS)+"\n"
def line(serial,parcel,node,at,received="2026-11-02T01:00:00Z",note="x"):
    return f"{serial},{parcel},{node},{at},{received},JP,24,200,0,{note}\n"

def test_event_uid_is_deterministic_and_ignores_serial():
    a=event_uid(("P1","收件","2026-11-02T00:00:00Z"))
    b=event_uid(("P1","收件","2026-11-02T00:00:00Z"))
    c=event_uid(("P2","收件","2026-11-02T00:00:00Z"))
    assert a==b and a.startswith("evt_") and a!=c

def test_same_serial_different_events_both_kept():
    "流水号每日复位：同号对应不同包裹，按号判重会吞掉真实扫描"
    raw=(HEADER+line("1001","P1","收件","2026-11-02T00:00:00Z")
              +line("1001","P2","收件","2026-11-02T03:00:00Z")).encode()
    r=evaluate(raw);m=r["metrics"]
    assert m["unique_events"]==2 and m["quarantine"]==0
    assert r["identity"]["reused_serials"]["1001"] and len(r["identity"]["reused_serials"]["1001"])==2
    assert m["balanced"] and m["input"]==m["accepted"]

def test_cross_warehouse_retransmission_merges_into_one_event():
    "跨仓补传换了本地流水号，但包裹/节点/时刻一致且整行相同：幂等合并为一个事件"
    raw=(HEADER+line("1004","P1","妥投","2026-11-04T00:00:00Z")
              +line("3010","P1","妥投","2026-11-04T00:00:00Z")).encode()
    r=evaluate(raw);m=r["metrics"]
    assert m["unique_events"]==1 and m["duplicate"]==1
    canonical=r["rows"][0]
    assert canonical["scan_serials"]==["1004","3010"] and canonical["_sources"]==[2,3]
    assert r["identity"]["events"][0]["scan_serials"]==["1004","3010"]

def test_retry_same_row_does_not_add_or_lose_event():
    "补传重试整行一致：事件全集不增不减，来源行可追回"
    raw=(HEADER+line("1001","P1","收件","2026-11-02T00:00:00Z")
              +line("1001","P1","收件","2026-11-02T00:00:00Z")).encode()
    r=evaluate(raw)
    assert r["metrics"]["unique_events"]==1 and r["metrics"]["accepted"]==2
    assert r["rows"][0]["_sources"]==[2,3]

def test_same_identity_different_content_is_quarantined_and_kept():
    "同一物理事件出现不同内容：隔离冲突行，原号原行保留，不覆盖首条"
    raw=(HEADER+line("1004","P1","妥投","2026-11-04T00:00:00Z",received="2026-11-04T02:00:00Z")
              +line("7777","P1","妥投","2026-11-04T00:00:00Z",received="2026-11-05T00:00:00Z")).encode()
    r=evaluate(raw)
    assert r["metrics"]["unique_events"]==1 and len(r["quarantine"])==1
    assert r["quarantine"][0]["reason"]=="EVENT_CONFLICT"
    assert r["rows"][0]["received_time"]=="2026-11-04T02:00:00Z"

def test_original_serial_preserved_textually():
    "仓库要求保留原流水：scan_id 与 scan_serials 均按字符串保形"
    r=evaluate((HEADER+line("0010","P1","收件","2026-11-02T00:00:00Z")).encode())
    assert r["rows"][0]["scan_id"]=="0010" and r["rows"][0]["scan_serials"]==["0010"]

def test_crosswarehouse_sample_full_pipeline_balanced():
    r=calculate(load_sample("crosswarehouse.csv"))
    m1=r["stages"][0]
    # 两个仓各有 1001/1002/1004 复位流水号
    assert set(m1["identity"]["reused_serials"])=={"1001","1002","1004"}
    # 1001 妥投事件被跨仓补传（3010 换号）合并；1001 收件被整行重试（3011）合并
    merged={e["event_uid"]:e for e in m1["identity"]["events"] if len(e["source_lines"])>1 or len(e["scan_serials"])>1}
    assert len(merged)>=2
    assert r["stages"][5]["metrics"]["balanced"] is True
    assert r["stages"][6]["metrics"]["ready"] is True

def test_timeliness_and_compensation_read_same_universe():
    r=calculate(load_sample("crosswarehouse.csv"))
    event_uids={x["event_uid"] for x in r["stages"][0]["rows"]}
    # 下游每个包裹路径都可回溯到唯一事件全集里的身份
    for parcel in r["stages"][3]["rows"]:
        assert parcel["parcel"] in {x["parcel"] for x in r["stages"][0]["rows"]}
    assert len(event_uids)==r["stages"][0]["metrics"]["unique_events"]
