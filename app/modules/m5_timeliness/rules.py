from datetime import datetime,timedelta,time
from zoneinfo import ZoneInfo
from decimal import Decimal
from app.values import instant,number,money
from app.errors import DomainError
HOLIDAYS={"JP":{"2026-11-03","2026-11-23"},"US":{"2026-11-26"},"DE":{"2026-10-03"}}
def working_hours(start,end,zone,holidays):
    if end<start:raise DomainError("NEGATIVE_INTERVAL","妥投早于收件")
    tz=ZoneInfo(zone);cursor=start;seconds=Decimal(0)
    while cursor<end:
        local=cursor.astimezone(tz);next_day=datetime.combine(local.date()+timedelta(days=1),time.min,tzinfo=tz).astimezone(cursor.tzinfo)
        stop=min(end,next_day)
        if local.weekday()<5 and local.date().isoformat() not in holidays:seconds+=Decimal(str((stop-cursor).total_seconds()))
        cursor=stop
    return seconds/3600
def evaluate(rows,context):
    p=context.get("parameters",{});as_of=instant(p.get("as_of","2026-11-18T00:00:00Z"));rate=number(p.get("hourly_compensation","1.00"))
    if rate<0:raise DomainError("BAD_RATE","赔付费率不能为负")
    good=[]
    for row in rows:
        start=instant(row["accepted_at"]);end=instant(row["delivered_at"]) if row.get("delivered_at") else max(start,as_of)
        hours=working_hours(start,end,row["zone"],set(p.get("holidays",{}).get(row["destination"],HOLIDAYS.get(row["destination"],set()))))
        late=max(Decimal(0),hours-number(row["promised_hours"]));comp=min(number(row["declared_value"])*Decimal("0.10"),late*rate)
        good.append({**row,"working_hours":str(hours),"late_hours":str(late),"expected":money(comp),"sla":"超时" if late>0 else "达标","clock_end":end.isoformat()})
    return {"rows":good,"quarantine":[],"metrics":{"parcels":len(good),"late_parcels":sum(r["sla"]=="超时" for r in good),"compensation":money(sum((number(r["expected"]) for r in good),Decimal(0)))}}
