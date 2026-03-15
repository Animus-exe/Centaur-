from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from ..models import CommodityPrice

BRENT_XLS = "https://www.eia.gov/dnav/pet/hist_xls/rbrted.xls"
WTI_XLS   = "https://www.eia.gov/dnav/pet/hist_xls/RWTCd.xls"

def _read_latest_price_from_eia_xls(url: str) -> tuple[datetime, float] | None:
    df = pd.read_excel(url, engine="xlrd")
    df = df.dropna()
    if len(df) == 0 or df.shape[1] < 2:
        return None
    ts = pd.to_datetime(df.iloc[-1, 0], utc=True).to_pydatetime()
    val = float(df.iloc[-1, 1])
    return (ts, val)

def ingest_eia_oil(db: Session, aois: list[dict] | None = None) -> int:
    inserted = 0
    result = _read_latest_price_from_eia_xls(BRENT_XLS)
    if result is not None:
        ts, price = result
        db.add(CommodityPrice(symbol="BRENT", name="Brent Spot", price=price, ts=ts, currency="USD", unit="USD/bbl", source="EIA", source_url=BRENT_XLS, raw={}))
        inserted += 1
    result2 = _read_latest_price_from_eia_xls(WTI_XLS)
    if result2 is not None:
        ts2, price2 = result2
        db.add(CommodityPrice(symbol="WTI", name="WTI Cushing Spot", price=price2, ts=ts2, currency="USD", unit="USD/bbl", source="EIA", source_url=WTI_XLS, raw={}))
        inserted += 1
    db.commit()
    return inserted
