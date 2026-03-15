import pandas as pd
from sqlalchemy.orm import Session
from ..models import CommodityPrice

STOOQ_XAUUSD_D = "https://stooq.com/q/d/l/?s=xauusd&i=d"

def ingest_stooq_gold(db: Session, aois: list[dict] | None = None) -> int:
    df = pd.read_csv(STOOQ_XAUUSD_D).dropna()
    last = df.iloc[-1]
    ts = pd.to_datetime(last["Date"], utc=True).to_pydatetime()
    close = float(last["Close"])
    db.add(CommodityPrice(symbol="XAUUSD", name="Gold (XAUUSD) Close", price=close, ts=ts, currency="USD", unit="USD/oz", source="stooq", source_url=STOOQ_XAUUSD_D, raw={"row": last.to_dict()}))
    db.commit()
    return 1
