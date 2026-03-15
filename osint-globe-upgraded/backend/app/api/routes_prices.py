from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from ..db import get_db
from ..models import CommodityPrice

router = APIRouter(prefix="/prices", tags=["prices"])

@router.get("/latest")
def latest_prices(db: Session = Depends(get_db)):
    symbols = [r[0] for r in db.execute(select(CommodityPrice.symbol).distinct()).all()]
    out = {}
    for sym in symbols:
        row = db.execute(select(CommodityPrice).where(CommodityPrice.symbol == sym).order_by(desc(CommodityPrice.ts)).limit(1)).scalars().first()
        if row:
            out[sym] = {
                "symbol": row.symbol,
                "name": row.name,
                "price": row.price,
                "currency": row.currency,
                "unit": row.unit,
                "ts": row.ts.isoformat() if row.ts else None,
                "source": row.source,
                "source_url": row.source_url,
            }
    return out
