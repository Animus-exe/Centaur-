import json
from datetime import datetime, timezone

def log(event: str, **fields):
    payload = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    print(json.dumps(payload, ensure_ascii=False))
