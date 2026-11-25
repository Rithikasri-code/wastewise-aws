"""Data shapes shared across the app.

Finding mirrors exactly the per-finding contract in the spec: resource id,
region, plain-language problem, evidence, estimated monthly savings, confidence
(with reason), suggested fix, and the config values that produced it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class PriceQuote:
    """A single on-demand price and where it came from."""

    service: str
    region: str
    unit: str
    price: float
    currency: str
    source: str  # "live" | "cache" | "cache_stale"
    fetched_at: str
    filters: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    """One piece of wasted spend. Populated by detectors in Phase 2."""

    resource_id: str
    resource_type: str
    region: str
    problem: str
    evidence: dict[str, Any]
    monthly_savings: float
    confidence: str  # "high" | "medium" | "low"
    confidence_reason: str
    suggested_fix: str
    config_values: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
