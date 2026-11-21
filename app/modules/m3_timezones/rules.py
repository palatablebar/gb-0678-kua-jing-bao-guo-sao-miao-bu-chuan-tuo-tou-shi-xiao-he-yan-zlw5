from app.values import instant,number
from app.reasons import reject
from app.errors import DomainError
def evaluate(rows,context):
    good=[];bad=[]
    for row in rows:
        try:
            event=instant(row["event_time"]);received=instant(row["received_time"]);promised=number(row["promised_hours"]);value=number(row["declared_value"]);reported=number(row["reported"])
            if received<event:raise DomainError("RECEIVED_BEFORE_EVENT","上传早于事件时间")
            if promised<0 or value<0 or reported<0:raise DomainError("NEGATIVE_VALUE","时限与金额不能为负")
            good.append({**row,"event_utc":event.isoformat(),"received_utc":received.isoformat(),"upload_lag_hours":str(number(str((received-event).total_seconds()))/3600),"promised_hours":str(promised),"declared_value":str(value),"reported":str(reported)})
        except (DomainError,KeyError) as e:bad.append(reject(row,getattr(e,"code","MISSING_FIELD"),str(e)))
    return {"rows":good,"quarantine":bad,"metrics":{"accepted":len(good),"late_uploads":sum(number(r["upload_lag_hours"])>24 for r in good)}}
