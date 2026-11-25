"""SQLite access and schema setup.

Three tables back the product:
  price_cache  - fetched AWS prices with timestamps (used by the pricing module)
  scans        - one row per analysis run, for the savings-over-time view later
  findings     - detected waste, normalized shape defined in models.Finding
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_cache (
    cache_key   TEXT PRIMARY KEY,
    service     TEXT NOT NULL,
    region      TEXT NOT NULL,
    filters     TEXT NOT NULL,
    unit        TEXT NOT NULL,
    price       REAL NOT NULL,
    currency    TEXT NOT NULL,
    fetched_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    mode          TEXT NOT NULL,
    regions       TEXT,
    findings_count INTEGER
);

CREATE TABLE IF NOT EXISTS findings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id           INTEGER,
    resource_id       TEXT NOT NULL,
    resource_type     TEXT NOT NULL,
    region            TEXT NOT NULL,
    problem           TEXT NOT NULL,
    evidence          TEXT NOT NULL,
    monthly_savings   REAL NOT NULL,
    confidence        TEXT NOT NULL,
    confidence_reason TEXT,
    suggested_fix     TEXT,
    config_values     TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    FOREIGN KEY (scan_id) REFERENCES scans (id)
);
"""


class Database:
    """Thin wrapper around a SQLite file."""

    def __init__(self, path: Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA)

    # ---- price_cache helpers ----
    def read_price(self, cache_key: str) -> Optional[dict]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM price_cache WHERE cache_key = ?", (cache_key,)
            ).fetchone()
            return dict(row) if row else None

    def write_price(
        self,
        cache_key: str,
        service: str,
        region: str,
        filters: dict,
        unit: str,
        price: float,
        currency: str,
        fetched_at: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO price_cache
                    (cache_key, service, region, filters, unit, price, currency, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    price = excluded.price,
                    currency = excluded.currency,
                    fetched_at = excluded.fetched_at
                """,
                (cache_key, service, region, json.dumps(filters, sort_keys=True), unit, price, currency, fetched_at),
            )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
