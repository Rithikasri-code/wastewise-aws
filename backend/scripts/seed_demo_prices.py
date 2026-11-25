"""One-time dev utility: build the demo price snapshot from REAL AWS prices.

The AWS Price List *Query* API needs credentials, so this is the step that does
require an AWS identity (any read-only one works). It reads the list of price
targets from config/price_targets.yaml, fetches each live, and writes a dated
JSON snapshot to the demo price snapshot path. Demo mode then loads that
snapshot into the price cache, so the app shows genuine AWS prices with no
credentials and never invents a number.

Usage (from backend/, with AWS credentials available):
    python scripts/seed_demo_prices.py

If a price cannot be fetched it is skipped with a warning - never faked.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

# Allow "python scripts/seed_demo_prices.py" from the backend dir.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_settings  # noqa: E402
from app.db import Database  # noqa: E402
from app.pricing import PricingService, PriceUnavailable  # noqa: E402


def main() -> int:
    settings = load_settings()
    targets_path = Path(settings.raw_app.get("demo", {}).get("price_targets_file", "config/price_targets.yaml"))
    if not targets_path.is_absolute():
        targets_path = Path(__file__).resolve().parent.parent / targets_path

    with targets_path.open("r", encoding="utf-8") as fh:
        targets = yaml.safe_load(fh)["targets"]

    db = Database(settings.database_path)
    db.init_schema()
    pricing = PricingService(
        db=db,
        pricing_api_region=settings.pricing_api_region,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        default_currency=settings.default_currency,
    )

    snapshot = []
    for t in targets:
        try:
            quote = pricing.get_price(
                service=t["service"], region=t["region"], filters=t.get("filters", {}), unit=t.get("unit", "Hrs")
            )
        except PriceUnavailable as exc:
            print(f"  skip {t['service']} {t['region']} {t.get('filters')}: {exc}")
            continue
        snapshot.append(
            {
                "service": quote.service,
                "region": quote.region,
                "filters": quote.filters,
                "unit": quote.unit,
                "price": quote.price,
                "currency": quote.currency,
                "captured_on": quote.fetched_at,
            }
        )
        print(f"  captured {quote.service} {quote.region} {quote.filters} = {quote.price} {quote.currency}/{quote.unit}")

    out = settings.demo_price_snapshot_file
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2)
    print(f"\nWrote {len(snapshot)} real prices to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
