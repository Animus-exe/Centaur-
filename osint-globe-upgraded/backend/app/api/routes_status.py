from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from ..db import get_db
from ..models import IngestJobStatus
from ..ingest.flights_airplanes_live import get_opensky_rate_limit_status

router = APIRouter(tags=["status"])

@router.get("/status")
def status(db: Session = Depends(get_db)):
    jobs = [r[0] for r in db.execute(select(IngestJobStatus.job_name).distinct()).all()]
    out = {"jobs": {}}
    for j in jobs:
        row = db.execute(
            select(IngestJobStatus).where(IngestJobStatus.job_name == j).order_by(desc(IngestJobStatus.ran_at)).limit(1)
        ).scalars().first()
        if row:
            out["jobs"][j] = {
                "ran_at": row.ran_at.isoformat() if row.ran_at else None,
                "duration_ms": row.duration_ms,
                "ok": row.ok,
                "item_count": row.item_count,
                "error": row.error,
            }
    out["flights"] = get_opensky_rate_limit_status()
    return out
