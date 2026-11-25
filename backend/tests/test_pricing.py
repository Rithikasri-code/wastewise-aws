"""Pricing module tests - run on their own, no network, no AWS calls.

A fake client is injected, so boto3 is never actually invoked. These prove the
core contract: live fetch parses correctly, results are cached, fresh cache is
served without refetching, an unreachable API falls back to the last cache and
is flagged stale, and there is no invented number when nothing is available.
"""
from __future__ import annotations

import json

import pytest

from app.db import Database
from app.models import PriceQuote
from app.pricing import PricingService, PriceUnavailable


class FakeClient:
    """Stand-in for the boto3 pricing client."""

    def __init__(self, responses, raise_error=False):
        self._responses = responses  # list of get_products responses
        self._raise = raise_error
        self.calls = 0
        self.last_kwargs = None

    def get_products(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        if self._raise:
            raise RuntimeError("AWS Price List API unreachable")
        # Return the last configured response (single-page in tests).
        return self._responses[-1]


def _product(price_usd: str) -> dict:
    """Build one minimal AWS Price List product record."""
    offer = {
        "product": {"attributes": {"instanceType": "m5.2xlarge", "operatingSystem": "Linux"}},
        "terms": {
            "OnDemand": {
                "SKU-1": {
                    "priceDimensions": {
                        "DIM-1": {
                            "pricePerUnit": {"USD": price_usd},
                            "unit": "Hrs",
                        }
                    }
                }
            }
        },
    }
    # PriceList entries are JSON strings, mirroring the real API shape.
    return json.dumps(offer)


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    d.init_schema()
    return d


def _service(db, ttl_seconds, client):
    return PricingService(
        db=db,
        pricing_api_region="us-east-1",
        cache_ttl_seconds=ttl_seconds,
        default_currency="USD",
        client_factory=lambda region: client,
    )


def test_live_fetch_parses_and_caches(db):
    client = FakeClient([{"PriceList": [_product("0.4800000000000000")]}])
    svc = _service(db, ttl_seconds=86400, client=client)

    quote = svc.get_price("AmazonEC2", "us-east-1", {"instanceType": "m5.2xlarge"})

    assert isinstance(quote, PriceQuote)
    assert quote.price == pytest.approx(0.48)
    assert quote.source == "live"
    assert quote.currency == "USD"
    assert client.calls == 1
    # Guard the real API contract: ServiceCode (not Service) and a region filter.
    assert client.last_kwargs["ServiceCode"] == "AmazonEC2"
    assert "ServiceRegion" not in client.last_kwargs
    filter_fields = {f["Field"]: f["Value"] for f in client.last_kwargs["Filters"]}
    assert filter_fields["region"] == "us-east-1"
    assert filter_fields["instanceType"] == "m5.2xlarge"
    # Result was persisted to the cache table.
    assert db.read_price(svc._cache_key("AmazonEC2", "us-east-1", {"instanceType": "m5.2xlarge"}, "USD")) is not None


def test_fresh_cache_is_served_without_refetching(db):
    client = FakeClient([{"PriceList": [_product("0.4800000000000000")]}])
    svc = _service(db, ttl_seconds=86400, client=client)
    svc.get_price("AmazonEC2", "us-east-1", {"instanceType": "m5.2xlarge"})
    assert client.calls == 1

    quote2 = svc.get_price("AmazonEC2", "us-east-1", {"instanceType": "m5.2xlarge"})
    assert quote2.source == "cache"
    assert quote2.price == pytest.approx(0.48)
    # No additional API call was made because the cache was still fresh.
    assert client.calls == 1


def test_unreachable_api_falls_back_to_stale_cache(db):
    # Prime the cache with a successful fetch.
    good = FakeClient([{"PriceList": [_product("0.4800000000000000")]}])
    _service(db, ttl_seconds=86400, client=good).get_price(
        "AmazonEC2", "us-east-1", {"instanceType": "m5.2xlarge"}
    )

    # ttl=0 forces the cache to be treated as expired, so a refetch is attempted.
    broken = FakeClient([], raise_error=True)
    svc = _service(db, ttl_seconds=0, client=broken)
    quote = svc.get_price("AmazonEC2", "us-east-1", {"instanceType": "m5.2xlarge"})

    assert quote.source == "cache_stale"
    assert quote.price == pytest.approx(0.48)
    assert broken.calls == 1  # it did try the live API first


def test_no_cache_and_unreachable_never_invents_a_number(db):
    broken = FakeClient([], raise_error=True)
    svc = _service(db, ttl_seconds=86400, client=broken)

    with pytest.raises(PriceUnavailable):
        svc.get_price("AmazonEC2", "us-east-1", {"instanceType": "unknown.type"})


def test_empty_response_raises_unavailable(db):
    client = FakeClient([{"PriceList": []}])
    svc = _service(db, ttl_seconds=86400, client=client)
    with pytest.raises(PriceUnavailable):
        svc.get_price("AmazonEC2", "us-east-1", {"instanceType": "nope"})


def test_seed_from_real_snapshot_then_serve_from_cache(db, tmp_path):
    """Demo path: a dated snapshot of real prices is loaded, then served from
    cache with no live call - and it is never an invented value."""
    from datetime import datetime, timedelta, timezone

    captured = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    snapshot = tmp_path / "snap.json"
    snapshot.write_text(
        json.dumps(
            [
                {
                    "service": "AmazonEC2",
                    "region": "us-east-1",
                    "filters": {"instanceType": "m5.2xlarge"},
                    "unit": "Hrs",
                    "price": 0.48,
                    "currency": "USD",
                    "captured_on": captured,
                }
            ]
        ),
        encoding="utf-8",
    )

    # A client that would fail if called - proving the snapshot is used instead.
    broken = FakeClient([], raise_error=True)
    svc = _service(db, ttl_seconds=86400, client=broken)
    assert svc.seed_cache_from_snapshot(snapshot) == 1

    quote = svc.get_price("AmazonEC2", "us-east-1", {"instanceType": "m5.2xlarge"})
    assert quote.price == pytest.approx(0.48)
    assert quote.source in ("cache", "cache_stale")
    assert broken.calls == 0  # served from the seeded snapshot, no live call


def test_seed_missing_file_is_noop(db, tmp_path):
    svc = _service(db, ttl_seconds=86400, client=FakeClient([]))
    assert svc.seed_cache_from_snapshot(tmp_path / "absent.json") == 0

