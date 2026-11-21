from collections import defaultdict
from app.values import instant
from app.reasons import reject,sources
PRIORITY={"ACCEPT":0,"DEPART":1,"CUSTOMS":2,"DELIVERED":3}
def evaluate(rows,context):
    groups=defaultdict(list);good=[];bad=[]
    for r in rows:groups[r["parcel"]].append(r)
    for parcel,events in sorted(groups.items()):
        events=sorted(events,key=lambda r:(instant(r["event_utc"]),PRIORITY[r["node"]],r["scan_id"]))
        seen={};valid=[];last=-1
        for e in events:
            time=e["event_utc"]
            if time in seen and seen[time]!=e["node"]:bad.append(reject(e,"SIMULTANEOUS_CONFLICT","同刻扫描节点冲突"));continue
            seen[time]=e["node"]
            if PRIORITY[e["node"]]<last:bad.append(reject(e,"PATH_REGRESSION","扫描路径倒退"));continue
            last=PRIORITY[e["node"]];valid.append(e)
        accepts=[e for e in valid if e["node"]=="ACCEPT"]
        if not accepts:
            bad.extend(reject(e,"MISSING_ACCEPT","缺少收件扫描") for e in valid);continue
        delivery=next((e for e in valid if e["node"]=="DELIVERED"),None)
        first=accepts[0]
        source_lines=[line for e in valid for line in sources(e)]
        good.append({**first,"_sources":source_lines,"accepted_at":first["event_utc"],"delivered_at":delivery["event_utc"] if delivery else None,"delivery_uploaded_at":delivery["received_utc"] if delivery else None,"scan_count":len(valid),"path":" → ".join(e["node"] for e in valid),"reported":delivery["reported"] if delivery else first["reported"]})
    return {"rows":good,"quarantine":bad,"metrics":{"parcels":len(good),"delivered":sum(r["delivered_at"] is not None for r in good),"path_errors":len(bad)}}
