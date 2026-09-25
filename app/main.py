"""Delivery metrics API backed by SQLite."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field


DB_PATH = os.getenv("CDN_ANALYTICS_DB", "cdn.db")


class DeliveryEvent(BaseModel):
    region: str = Field(min_length=1, max_length=64)
    provider: str = Field(min_length=1, max_length=64)
    cache_hit: bool
    bytes_sent: int = Field(gt=0)
    latency_ms: float = Field(gt=0)
    origin_bytes: int = Field(default=0, ge=0)
    event_time: datetime | None = None


class MetricsSummary(BaseModel):
    event_count: int
    cache_hit_ratio: float
    average_latency_ms: float
    bandwidth_gb: float
    origin_traffic_gb: float
    estimated_cost: float


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS delivery_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region TEXT NOT NULL,
                provider TEXT NOT NULL,
                cache_hit INTEGER NOT NULL,
                bytes_sent INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                origin_bytes INTEGER NOT NULL,
                event_time TEXT NOT NULL
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_delivery_region ON delivery_events(region)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_delivery_time ON delivery_events(event_time)")


def event_time(value: datetime | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def summary_from_row(row: sqlite3.Row | None) -> MetricsSummary:
    if row is None or row["event_count"] == 0:
        return MetricsSummary(event_count=0, cache_hit_ratio=0, average_latency_ms=0, bandwidth_gb=0, origin_traffic_gb=0, estimated_cost=0)
    bandwidth_gb = row["total_bytes"] / 1_000_000_000
    origin_gb = row["origin_bytes"] / 1_000_000_000
    return MetricsSummary(
        event_count=row["event_count"],
        cache_hit_ratio=round(row["cache_hits"] / row["event_count"], 4),
        average_latency_ms=round(row["average_latency"], 2),
        bandwidth_gb=round(bandwidth_gb, 6),
        origin_traffic_gb=round(origin_gb, 6),
        estimated_cost=round(bandwidth_gb * .012, 6),
    )


app = FastAPI(title="CDN Traffic Analytics", version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/events", status_code=201)
def record_event(event: DeliveryEvent) -> dict[str, int | str]:
    with connect() as conn:
        cursor = conn.execute(
            """INSERT INTO delivery_events(region, provider, cache_hit, bytes_sent, latency_ms, origin_bytes, event_time)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event.region, event.provider, int(event.cache_hit), event.bytes_sent, event.latency_ms, event.origin_bytes, event_time(event.event_time)),
        )
    return {"id": cursor.lastrowid, "status": "recorded"}


@app.get("/v1/metrics/summary", response_model=MetricsSummary)
def metrics_summary(
    region: str | None = Query(default=None, max_length=64),
    provider: str | None = Query(default=None, max_length=64),
) -> MetricsSummary:
    with connect() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS event_count,
                      COALESCE(SUM(cache_hit), 0) AS cache_hits,
                      COALESCE(AVG(latency_ms), 0) AS average_latency,
                      COALESCE(SUM(bytes_sent), 0) AS total_bytes,
                      COALESCE(SUM(origin_bytes), 0) AS origin_bytes
               FROM delivery_events
               WHERE (? IS NULL OR region = ?)
                 AND (? IS NULL OR provider = ?)""",
            (region, region, provider, provider),
        ).fetchone()
    return summary_from_row(row)


@app.delete("/v1/events")
def clear_events() -> dict[str, int]:
    with connect() as conn:
        result = conn.execute("DELETE FROM delivery_events")
    return {"deleted": result.rowcount}

