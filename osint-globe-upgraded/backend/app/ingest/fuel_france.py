from datetime import datetime, timezone
from sqlalchemy.orm import Session
from lxml import etree
import zipfile, io

from ..models import FuelStationPrice
from .util_http import get_client, get_with_retry

FR_INSTANT = "https://donnees.roulez-eco.fr/opendata/instantane"

def ingest_fuel_france(db: Session, aois: list[dict]) -> int:
    client = get_client()
    r = get_with_retry(FR_INSTANT, client)
    if r.status_code in (304,):
        return 0
    if r.status_code != 200:
        return 0

    z = zipfile.ZipFile(io.BytesIO(r.content))
    xml_name = [n for n in z.namelist() if n.lower().endswith(".xml")][0]
    root = etree.fromstring(z.read(xml_name))
    now = datetime.now(timezone.utc)
    inserted = 0

    for pdv in root.findall(".//pdv"):
        sid = pdv.get("id")
        lat_raw = pdv.get("latitude"); lon_raw = pdv.get("longitude")
        if not sid or not lat_raw or not lon_raw: continue
        try:
            lat = float(lat_raw) / 100000.0
            lon = float(lon_raw) / 100000.0
        except (TypeError, ValueError):
            continue

        if aois:
            inside = any(a["minLat"] <= lat <= a["maxLat"] and a["minLon"] <= lon <= a["maxLon"] for a in aois)
            if not inside: continue

        for prix in pdv.findall(".//prix"):
            fuel_name = (prix.get("nom") or "").strip()
            val = prix.get("valeur")
            if not fuel_name or val is None: continue
            try:
                price = float(val)
            except (TypeError, ValueError):
                continue
            currency = (prix.get("devise") or "EUR").strip()
            maj = prix.get("maj")
            db.add(FuelStationPrice(provider="france", station_id=str(sid), country="FR", fuel_type=fuel_name, price_per_l=price, currency=currency, observed_at=now, lat=lat, lon=lon, raw={"maj": maj}))
            inserted += 1

    db.commit()
    return inserted
