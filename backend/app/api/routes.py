"""HTTP routes.

Phase 1 exposes the pieces needed to prove the foundation works end-to-end:
  /api/health          - liveness
  /api/branding        - product name + tagline (from the language file)
  /api/language        - full on-screen text bundle
  /api/config          - detector rule defaults (for the future Settings page)
  /api/demo/account    - the fake account loaded from the editable seed
  /api/pricing/quote   - run a price through the live+cache+fallback pipeline

All branding and copy come from the backend language file, so the frontend
never hardcodes the product name or tagline.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..pricing import PriceUnavailable

router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "demo_mode": settings.demo_enabled,
        "currency": settings.default_currency,
    }


@router.get("/branding")
def branding(request: Request) -> dict:
    return request.app.state.language.get("branding", {})


@router.get("/language")
def language(request: Request) -> dict:
    return request.app.state.language


@router.get("/config")
def config(request: Request) -> dict:
    return {"rules": request.app.state.rules}


@router.get("/demo/account")
def demo_account(request: Request) -> dict:
    if request.app.state.demo_account is None:
        return {"enabled": False, "account": None}
    return {
        "enabled": True,
        "source_file": str(request.app.state.settings.demo_seed_file),
        "account": request.app.state.demo_account.to_dict(),
    }


@router.post("/pricing/quote")
async def pricing_quote(request: Request) -> dict:
    """Quote a single on-demand price through the pricing pipeline."""
    body = await request.json()
    service = body.get("service")
    region = body.get("region")
    filters = body.get("filters", {})
    unit = body.get("unit", "Hrs")
    if not service or not region:
        return {"error": "service and region are required"}

    pricing = request.app.state.pricing
    try:
        quote = pricing.get_price(service=service, region=region, filters=filters, unit=unit)
    except PriceUnavailable as exc:
        return {"error": str(exc)}
    return quote.to_dict()
