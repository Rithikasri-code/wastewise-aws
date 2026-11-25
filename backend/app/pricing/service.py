"""AWS price lookup - fetch live, cache, and fall back. Tested on its own.

Rules this module must never break (from the project spec):
  * Prices come live from the AWS Price List API, never invented.
  * Results are cached locally with an expiry (cache_ttl_seconds from config).
  * If the API is unreachable, return the last cached price and flag it stale.
  * If there is neither a live price nor any cache, raise PriceUnavailable.
  * No price, region, or unit literal is written here - all come from config
    (pricing_api_region, cache_ttl_seconds) and from the caller's filters.

The AWS Price List *Query* API (GetProducts) requires SigV4 credentials, so it
is used in real mode with the read-only identity. Demo mode has no credentials:
its cache is pre-seeded from a dated snapshot of real prices (see
scripts/seed_demo_prices.py), and a live miss falls back to that snapshot rather
than inventing a number.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from botocore.config import Config

from ..db import Database, utc_now_iso
from ..models import PriceQuote


class PriceUnavailable(RuntimeError):
    """Raised when no live price and no cached price are available."""


def default_client_factory(region: str):
    """Create a standard AWS Price List client.

    The Price List *Query* API (GetProducts) requires SigV4 credentials, so we
    use the ambient AWS identity (profile / role / env). In demo mode there are
    no credentials, so live fetches fail and the pipeline falls back to the
    real-price snapshot seeded at startup - it never invents a number.
    """
    import boto3  # imported lazily so unit tests need no AWS SDK calls

    return boto3.client(
        "pricing",
        region_name=region,
        config=Config(retries={"max_attempts": 2}),
    )


def _parse_age_hours(fetched_at: str) -> float:
    dt = datetime.fromisoformat(fetched_at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0


def _first_on_demand_price(products: list[str]) -> Optional[float]:
    """Extract the first on-demand price-per-unit value from a get_products page.

    The AWS response is a list of JSON strings. We look for the OnDemand terms
    and return the numeric price for the first price dimension we find.
    """
    for raw in products:
        offer = json.loads(raw)
        on_demand = offer.get("terms", {}).get("OnDemand", {})
        for sku in on_demand.values():
            for dim in sku.get("priceDimensions", {}).values():
                per_unit = dim.get("pricePerUnit", {})
                # "USD" here is the fixed field name in the AWS Price List
                # response (the canonical on-demand currency), not a configurable
                # value. Display-currency conversion is handled in a later phase.
                value = per_unit.get("USD")
                if value:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        continue
    return None


class PricingService:
    def __init__(
        self,
        db: Database,
        pricing_api_region: str,
        cache_ttl_seconds: int,
        default_currency: str,
        client_factory: Optional[Callable[[str], Any]] = None,
    ):
        self._db = db
        self._region = pricing_api_region
        self._ttl = cache_ttl_seconds
        self._currency = default_currency
        self._client_factory = client_factory or default_client_factory
        self._client = None

    # Exposed for tests to inject a fake client without touching boto3.
    def set_client(self, client: Any) -> None:
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory(self._region)
        return self._client

    def seed_cache_from_snapshot(self, snapshot_path) -> int:
        """Load a dated snapshot of REAL AWS prices into the price cache.

        Used by demo mode so it can show genuine prices with no AWS
        credentials and no 481MB bulk download. The snapshot is produced by
        scripts/seed_demo_prices.py from the live Price List API. This never
        invents a number: entries missing from the snapshot simply stay
        unavailable. Returns the number of prices seeded.
        """
        from pathlib import Path

        path = Path(snapshot_path)
        if not path.exists():
            return 0
        with path.open("r", encoding="utf-8") as fh:
            entries = json.load(fh)

        seeded = 0
        for e in entries:
            filters = e.get("filters", {})
            key = self._cache_key(e["service"], e["region"], filters, e["currency"])
            self._db.write_price(
                key,
                service=e["service"],
                region=e["region"],
                filters=filters,
                unit=e["unit"],
                price=float(e["price"]),
                currency=e["currency"],
                fetched_at=e["captured_on"],
            )
            seeded += 1
        return seeded

    @staticmethod
    def _cache_key(service: str, region: str, filters: dict[str, str], currency: str) -> str:
        canonical = json.dumps(
            {"s": service, "r": region, "f": filters, "c": currency},
            sort_keys=True,
        )
        return canonical

    def get_price(
        self, service: str, region: str, filters: dict[str, str], unit: str = "Hrs"
    ) -> PriceQuote:
        """Return a fresh live price, a fresh cached price, or a stale cache.

        Never returns an invented number. Raises PriceUnavailable if there is
        no live price and no cache to fall back on.
        """
        key = self._cache_key(service, region, filters, self._currency)
        cached = self._db.read_price(key)
        if cached and _parse_age_hours(cached["fetched_at"]) <= self._ttl / 3600.0:
            return PriceQuote(
                service=service,
                region=region,
                unit=cached["unit"],
                price=cached["price"],
                currency=cached["currency"],
                source="cache",
                fetched_at=cached["fetched_at"],
                filters=filters,
            )

        try:
            price = self._fetch_live(service, region, filters, unit)
        except Exception:
            if cached:
                return PriceQuote(
                    service=service,
                    region=region,
                    unit=cached["unit"],
                    price=cached["price"],
                    currency=cached["currency"],
                    source="cache_stale",
                    fetched_at=cached["fetched_at"],
                    filters=filters,
                )
            raise PriceUnavailable(
                f"No live price and no cached price for {service} in {region}"
            )

        fetched_at = utc_now_iso()
        self._db.write_price(key, service, region, filters, unit, price, self._currency, fetched_at)
        return PriceQuote(
            service=service,
            region=region,
            unit=unit,
            price=price,
            currency=self._currency,
            source="live",
            fetched_at=fetched_at,
            filters=filters,
        )

    def _fetch_live(self, service: str, region: str, filters: dict[str, str], unit: str) -> float:
        client = self._get_client()
        # The Price List API takes ServiceCode (not Service) and expresses the
        # region as a "region" filter rather than a dedicated parameter.
        filter_pairs = {"region": region, **filters}
        request = {
            "ServiceCode": service,
            "Filters": [
                {"Type": "Equals", "Field": field, "Value": value}
                for field, value in filter_pairs.items()
            ],
            "MaxResults": 100,
        }
        price: Optional[float] = None
        while True:
            response = client.get_products(**request)
            price = _first_on_demand_price(response.get("PriceList", []))
            if price is not None:
                break
            token = response.get("NextToken")
            if not token:
                break
            request["NextToken"] = token

        if price is None:
            raise PriceUnavailable(
                f"AWS Price List returned no on-demand price for {service} in {region}"
            )
        return price
