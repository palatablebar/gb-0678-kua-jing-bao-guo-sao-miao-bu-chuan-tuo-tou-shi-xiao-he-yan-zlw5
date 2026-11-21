from app.reasons import reject
NODES={"收件":"ACCEPT","ACCEPT":"ACCEPT","起运":"DEPART","DEPART":"DEPART","清关":"CUSTOMS","CUSTOMS":"CUSTOMS","妥投":"DELIVERED","DELIVERED":"DELIVERED"}
DESTINATIONS={"JP":"Asia/Tokyo","US":"America/New_York","DE":"Europe/Berlin"}
def evaluate(rows,context):
    good=[];bad=[]
    for row in rows:
        node=NODES.get(row.get("node"));zone=DESTINATIONS.get(row.get("destination"))
        if not node:bad.append(reject(row,"UNKNOWN_NODE","扫描节点未登记"));continue
        if not zone:bad.append(reject(row,"UNKNOWN_DESTINATION","目的地未登记"));continue
        if not row.get("parcel"):bad.append(reject(row,"EMPTY_PARCEL","包裹号为空"));continue
        good.append({**row,"node":node,"zone":zone})
    return {"rows":good,"quarantine":bad,"metrics":{"accepted":len(good),"destinations":sorted(set(r["destination"] for r in good))}}
