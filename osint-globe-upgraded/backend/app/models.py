from sqlalchemy import String, Integer, Float, DateTime, JSON, Index, UniqueConstraint, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .db import Base

class IngestJobStatus(Base):
    __tablename__ = "ingest_job_status"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(96), index=True)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    __table_args__ = (Index("ix_ingest_job_name_ran_at", "job_name", "ran_at"),)

class FlightState(Base):
    __tablename__ = "flight_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    icao24: Mapped[str] = mapped_column(String(16), index=True)
    callsign: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    altitude_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    velocity_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(64), default="unknown")
    raw: Mapped[dict] = mapped_column(JSON, default={})
    __table_args__ = (
        UniqueConstraint("icao24", name="uq_flightstate_icao24"),
        Index("ix_flightstate_latlon", "lat", "lon"),
    )

class FlightTrackPoint(Base):
    __tablename__ = "flight_track_point"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    icao24: Mapped[str] = mapped_column(String(16), index=True)
    callsign: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    altitude_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    velocity_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64), default="unknown")
    raw: Mapped[dict] = mapped_column(JSON, default={})
    __table_args__ = (
        Index("ix_track_icao_ts", "icao24", "ts"),
        Index("ix_track_lat_lon", "lat", "lon"),
    )

class ConflictAreaEvent(Base):
    __tablename__ = "conflict_area_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), default="ucdp")
    source_event_id: Mapped[str] = mapped_column(String(96), index=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    category: Mapped[str] = mapped_column(String(64), default="conflict")
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    geometry_wkt: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchor_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    anchor_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_tier: Mapped[str] = mapped_column(String(32), default="AREA_ONLY")
    anchor_method: Mapped[str] = mapped_column(String(32), default="representative_point")
    precision_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    fatalities: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw: Mapped[dict] = mapped_column(JSON, default={})
    __table_args__ = (UniqueConstraint("source", "source_event_id", name="uq_conflict_source_event"),)

class CommodityPrice(Base):
    __tablename__ = "commodity_price"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    currency: Mapped[str] = mapped_column(String(16), default="USD")
    unit: Mapped[str] = mapped_column(String(32), default="")
    price: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(64), default="")
    source_url: Mapped[str] = mapped_column(String(512), default="")
    raw: Mapped[dict] = mapped_column(JSON, default={})
    __table_args__ = (Index("ix_commodity_symbol_ts", "symbol", "ts"),)

class FuelStationPrice(Base):
    __tablename__ = "fuel_station_price"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), default="france")
    station_id: Mapped[str] = mapped_column(String(64), index=True)
    country: Mapped[str] = mapped_column(String(2), default="FR")
    fuel_type: Mapped[str] = mapped_column(String(64), index=True)
    price_per_l: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    raw: Mapped[dict] = mapped_column(JSON, default={})
    __table_args__ = (
        Index("ix_fuel_lat_lon", "lat", "lon"),
        Index("ix_fuel_provider_station_fuel_time", "provider", "station_id", "fuel_type", "observed_at"),
    )


class IpCameraCity(Base):
    """Persisted IP camera aggregates by city (Shodan). Kept so cameras appear after restart."""
    __tablename__ = "ip_camera_city"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city: Mapped[str] = mapped_column(String(128), index=True)
    country_code: Mapped[str] = mapped_column(String(4), index=True)
    country_name: Mapped[str] = mapped_column(String(128), default="")
    lon: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    cameras: Mapped[list] = mapped_column(JSON, default=list)  # list of {ip, port, product, link}
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    __table_args__ = (UniqueConstraint("city", "country_code", name="uq_ip_camera_city_country"),)
