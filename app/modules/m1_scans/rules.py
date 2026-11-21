import csv,io,hashlib,json
from app.config import COLUMNS
from app.errors import DomainError
from app.reasons import reject

# 身份认定：scan_id 是终端本地日流水号（跨终端、跨天会重复），只能作溯源别名。
# 扫描事件的规范身份由物理事件三要素决定：包裹号 + 节点 + 事件发生时刻。
IDENTITY_FIELDS=("parcel","node","event_time")
# 原流水号是终端本地别名，不属于事件内容；判等时比较除 scan_id 外的全部载荷
PAYLOAD_FIELDS=tuple(f for f in COLUMNS if f!="scan_id")

def decode(raw):
    for encoding in ("utf-8-sig","gb18030"):
        try: return raw.decode(encoding),encoding
        except UnicodeDecodeError: continue
    raise DomainError("ENCODING","无法识别文件编码")

def event_uid(identity):
    """对 (parcel,node,event_time) 做确定性派生，跨补传、跨重跑稳定。"""
    token=json.dumps(identity,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return "evt_"+hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]

def payload(row):
    return tuple(row[f] for f in PAYLOAD_FIELDS)

def evaluate(raw,context=None):
    text,encoding=decode(raw)
    if not text: raise DomainError("EMPTY_FILE","文件为空")
    if not text.strip(): raise DomainError("BLANK_ONLY","全部为空行")
    stream=csv.reader(io.StringIO(text,newline=""));header=next(stream,None)
    if header!=COLUMNS: raise DomainError("BAD_HEADER","表头不匹配")
    rows=[];bad=[];duplicate=blank=repeated=count=0
    # 规范身份 -> 已采纳规范事件；本地流水号 -> 命中过的 event_uid 列表（页面解释同号关系）
    events={};aliases={}
    try:
        for cells in stream:
            count+=1;line=stream.line_num
            if not cells or not any(c.strip() for c in cells): blank+=1;continue
            if cells==header: repeated+=1;continue
            row={"_line":line,"_sources":[line],"_raw":cells}
            if len(cells)!=len(header): bad.append(reject(row,"BAD_COLUMNS","列数不匹配"));continue
            row.update(dict(zip(header,[x.strip() for x in cells])))
            if not row[header[0]]: bad.append(reject(row,"EMPTY_VALUE","业务键为空"));continue
            serial=row["scan_id"]
            # 1) 先认定物理事件身份：包裹 + 节点 + 发生时刻；要素缺失则隔离且不吞号
            identity=tuple(row[f] for f in IDENTITY_FIELDS)
            if not all(identity):
                bad.append(reject(row,"EMPTY_IDENTITY","事件身份要素缺失（包裹/节点/发生时刻）"));continue
            uid=event_uid(identity)
            aliases.setdefault(serial,[])
            if uid not in aliases[serial]: aliases[serial].append(uid)
            if uid in events:
                canonical=events[uid]
                # 2) 同一物理事件：除流水号外载荷一致才幂等合并（无论原流水号是否相同），不新增事件
                if payload(row)==payload(canonical):
                    duplicate+=1
                    if line not in canonical["_sources"]: canonical["_sources"].append(line)
                    if serial not in canonical["scan_serials"]: canonical["scan_serials"].append(serial)
                    continue
                # 3) 同身份异内容：不覆盖、不吞掉，隔离待人工裁决，原号原行保留
                bad.append(reject(row,"EVENT_CONFLICT","同一包裹/节点/时刻出现不同内容"));continue
            # 4) 新物理事件：原流水号可能与他事件相同（终端每日复位），不再按号判重
            row["event_uid"]=uid
            row["identity_key"]=list(identity)
            row["scan_serials"]=[serial]
            events[uid]=row;rows.append(row)
    except csv.Error: raise DomainError("BAD_CSV","引号未闭合或文件损坏")
    if count==0: raise DomainError("HEADER_ONLY","仅有表头")
    if not rows and not bad: raise DomainError("BLANK_ONLY","全部为空行")
    # 页面/API 解释材料：哪些原号相同（一个流水号对应多个事件）、哪些记录属于同一事件（一个事件多个原号/多行）
    reused_serials={s:uids for s,uids in sorted(aliases.items()) if len(uids)>1}
    identity_index=[{"event_uid":r["event_uid"],"identity":r["identity_key"],
                     "scan_serials":r["scan_serials"],"source_lines":r["_sources"]}
                    for r in sorted(rows,key=lambda r:r["event_uid"])]
    retransmitted=sum(1 for r in rows if len(r["_sources"])>1 or len(r["scan_serials"])>1)
    accepted_lines=sum(len(r["_sources"]) for r in rows)
    # 行数守恒：输入逻辑行 = 采纳来源行（含幂等合并行）+ 隔离行 + 空行 + 分段表头；无“被丢弃”的行
    return {"rows":rows,"quarantine":bad,
            "identity":{"events":identity_index,"serial_aliases":aliases,"reused_serials":reused_serials},
            "metrics":{"input":count,"accepted":accepted_lines,"accepted_events":len(rows),"quarantine":len(bad),
                       "duplicate":duplicate,"blank":blank,"repeated_headers":repeated,"encoding":encoding,
                       "unique_events":len(rows),"reused_serial_count":len(reused_serials),
                       "retransmitted_events":retransmitted,
                       "balanced":count==accepted_lines+len(bad)+blank+repeated}}
