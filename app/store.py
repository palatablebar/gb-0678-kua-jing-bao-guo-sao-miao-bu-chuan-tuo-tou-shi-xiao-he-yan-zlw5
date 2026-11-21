import sqlite3,json,os,hashlib,tempfile
from datetime import datetime,timezone
from app.config import DATA_DIR
from app.errors import DomainError
def connect():
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DATA_DIR/"records.db",timeout=20)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY,payload TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,decision TEXT NOT NULL DEFAULT '待复核')")
    db.execute("CREATE TABLE IF NOT EXISTS published (singleton INTEGER PRIMARY KEY CHECK(singleton=1),run_id TEXT NOT NULL,published_at TEXT NOT NULL,FOREIGN KEY(run_id) REFERENCES runs(id))")
    return db
def save(run_id,payload):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO runs(id,payload) VALUES (?,?)",(run_id,json.dumps(payload,ensure_ascii=False)))
    return get(run_id)
def get(run_id):
    with connect() as db: row=db.execute("SELECT payload,version,decision FROM runs WHERE id=?",(run_id,)).fetchone()
    if not row: raise DomainError("NOT_FOUND","批次不存在",404)
    return {**json.loads(row[0]),"version":row[1],"decision":row[2]}
def latest():
    with connect() as db: row=db.execute("SELECT id FROM runs ORDER BY rowid DESC LIMIT 1").fetchone()
    return get(row[0]) if row else None
def history():
    with connect() as db: return [{"run_id":i,"version":v,"decision":d} for i,v,d in db.execute("SELECT id,version,decision FROM runs ORDER BY rowid DESC")]
def review(run_id,version,decision):
    if decision not in {"已复核","退回复核"}: raise DomainError("BAD_DECISION","复核状态无效")
    with connect() as db:
        cursor=db.execute("UPDATE runs SET version=version+1,decision=? WHERE id=? AND version=?",(decision,run_id,version))
        if cursor.rowcount!=1:
            if not db.execute("SELECT 1 FROM runs WHERE id=?",(run_id,)).fetchone(): raise DomainError("NOT_FOUND","批次不存在",404)
            raise DomainError("STALE_VERSION","版本已更新，请刷新",409)
    return get(run_id)
def _publishable(payload):
    stages=payload.get("stages",[])
    if len(stages)<7: return False
    reconcile=stages[5].get("metrics",{})
    return bool(reconcile.get("balanced")) and bool(stages[6].get("metrics",{}).get("ready"))
def publish(run_id):
    """单事务发布：任一步失败整体回滚，已发布指针保持旧版批次。"""
    with connect() as db:
        row=db.execute("SELECT payload FROM runs WHERE id=?",(run_id,)).fetchone()
        if not row: raise DomainError("NOT_FOUND","批次不存在",404)
        if not _publishable(json.loads(row[0])): raise DomainError("UNPUBLISHABLE","行数未对平或未达归档条件，禁止发布")
        db.execute("INSERT INTO published(singleton,run_id,published_at) VALUES(1,?,?) ON CONFLICT(singleton) DO UPDATE SET run_id=excluded.run_id,published_at=excluded.published_at",(run_id,datetime.now(timezone.utc).isoformat()))
    return published()
def published():
    with connect() as db: row=db.execute("SELECT run_id,published_at FROM published WHERE singleton=1").fetchone()
    if not row: return None
    run=get(row[0]);run["published_at"]=row[1];return run
def preserve_raw(raw):
    """原始上传字节按 sha256 内容寻址落盘：只写、不覆盖、不删除，补传重试共用同一份原件。"""
    sha=hashlib.sha256(raw).hexdigest();folder=DATA_DIR/"raw";path=folder/(sha+".csv")
    if not path.exists():
        folder.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix=sha+".",suffix=".tmp",dir=folder)
        try:
            with os.fdopen(fd,"wb") as handle: handle.write(raw)
            os.replace(tmp,path)
        except BaseException:
            if os.path.exists(tmp): os.unlink(tmp)
            raise
    return sha,path
def raw_path(run_id):
    sha=get(run_id)["manifest"]["input_sha256"];path=DATA_DIR/"raw"/(sha+".csv")
    if not path.exists(): raise DomainError("RAW_MISSING","原始文件未留存",404)
    return sha,path
