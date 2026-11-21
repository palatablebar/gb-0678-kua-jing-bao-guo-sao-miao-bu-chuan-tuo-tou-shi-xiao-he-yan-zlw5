import json
from app.pipeline import execute,load_sample
from app import store
from app.errors import DomainError
import pytest

def test_raw_bytes_preserved_content_addressed(tmp_path,monkeypatch,sample):
    monkeypatch.setattr(store,"DATA_DIR",tmp_path)
    run=execute(sample)
    sha,path=store.raw_path(run["run_id"])
    assert path.read_bytes()==sample and sha==run["manifest"]["input_sha256"]

def test_retry_shares_one_raw_and_keeps_scans(tmp_path,monkeypatch,sample):
    monkeypatch.setattr(store,"DATA_DIR",tmp_path)
    a=execute(sample);b=execute(sample)
    assert a["run_id"]==b["run_id"]
    files=list((tmp_path/"raw").glob("*.csv"))
    assert len(files)==1  # 内容寻址：补传重试不产生重复原件
    assert a["stages"][0]["metrics"]["unique_events"]==b["stages"][0]["metrics"]["unique_events"]

def test_publish_then_failed_publish_keeps_previous_batch(tmp_path,monkeypatch):
    monkeypatch.setattr(store,"DATA_DIR",tmp_path)
    good=execute(load_sample("crosswarehouse.csv"))
    assert store.publish(good["run_id"])["run_id"]==good["run_id"]
    # 构造一个不可发布批次（未对平/未归档），直接落库
    bad_payload={"stages":[{"metrics":{}}]*5+[{"metrics":{"balanced":False}},{"metrics":{"ready":False}}]}
    with store.connect() as db:
        db.execute("INSERT INTO runs(id,payload) VALUES(?,?)",("badrun",json.dumps(bad_payload)))
    with pytest.raises(DomainError) as e: store.publish("badrun")
    assert e.value.code=="UNPUBLISHABLE"
    # 失败后已发布指针仍是旧版批次
    assert store.published()["run_id"]==good["run_id"]
    # 不存在的批次不影响指针
    with pytest.raises(DomainError): store.publish("ghost")
    assert store.published()["run_id"]==good["run_id"]

def test_publish_second_valid_batch_switches_pointer(tmp_path,monkeypatch):
    monkeypatch.setattr(store,"DATA_DIR",tmp_path)
    first=execute(load_sample("crosswarehouse.csv"));store.publish(first["run_id"])
    second=execute(load_sample("clean.csv"));store.publish(second["run_id"])
    assert store.published()["run_id"]==second["run_id"]
    # 旧版批次仍可完整取回，未被删除
    assert store.get(first["run_id"])["run_id"]==first["run_id"]

def test_published_api_404_when_none(client):
    assert client.get("/api/published").status_code==404

def test_publish_and_raw_endpoints(client):
    p=client.post("/api/runs",json={"sample":"crosswarehouse.csv"}).get_json()
    ok=client.post(f"/api/runs/{p['run_id']}/publish")
    assert ok.status_code==200 and ok.get_json()["run_id"]==p["run_id"]
    assert client.get("/api/published").status_code==200
    raw=client.get(f"/api/runs/{p['run_id']}/raw")
    assert raw.status_code==200 and raw.data==load_sample("crosswarehouse.csv")

def test_unpublishable_batch_rejected_by_api(client):
    # 直接落库一个未对平批次，发布接口必须拒绝且不动指针
    bad_payload={"stages":[{"metrics":{}}]*5+[{"metrics":{"balanced":False}},{"metrics":{"ready":False}}]}
    with store.connect() as db:
        db.execute("INSERT INTO runs(id,payload) VALUES(?,?)",("badbatch",json.dumps(bad_payload)))
    resp=client.post("/api/runs/badbatch/publish")
    assert resp.status_code==422 and resp.get_json()["code"]=="UNPUBLISHABLE"
    assert client.get("/api/published").status_code==404
