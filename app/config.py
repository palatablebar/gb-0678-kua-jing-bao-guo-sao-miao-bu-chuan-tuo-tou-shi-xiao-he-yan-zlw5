from pathlib import Path
import os
ROOT=Path(__file__).resolve().parent.parent
DATA_DIR=Path(os.environ.get("DATA_DIR", "/tmp/parcelsla"))
TITLE='跨境包裹扫描补传与妥投时效核验'
SHORT='parcelsla'
COLUMNS=['scan_id', 'parcel', 'node', 'event_time', 'received_time', 'destination', 'promised_hours', 'declared_value', 'reported', 'note']
MODULES=[('scans', '扫描采信'), ('nodes', '节点映射'), ('timezones', '时区归整'), ('paths', '路径裁决'), ('timeliness', '时效计算'), ('compensation', '赔付对账'), ('archives', '批次归档')]
RULE_VERSION="2026.11.17-r1"
