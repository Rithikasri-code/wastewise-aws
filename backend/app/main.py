"""FastAPI application entry point.

On startup we load config, open SQLite, create the pricing service, and load
the demo account. Nothing here hardcodes branding, thresholds, regions, or
prices - all of that is read from config files via app.config.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.routes import router
from .config import load_language, load_rules, load_settings
from .db import Database
from .demo import load_demo_account
from .pricing import PricingService


def create_app() -> FastAPI:
    settings = load_settings()
    language = load_language(settings)
    # API title comes from the branding in the language file, never hardcoded.
    app = FastAPI(
        title=language.get("branding", {}).get("full_name", "API"),
        version=__version__,
    )

    db = Database(settings.database_path)
    db.init_schema()

    app.state.settings = settings
    app.state.db = db
    app.state.rules = load_rules(settings)
    app.state.language = language
    app.state.pricing = PricingService(
        db=db,
        pricing_api_region=settings.pricing_api_region,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        default_currency=settings.default_currency,
    )
    # Demo mode: load the fake account from the editable seed file.
    app.state.demo_account = load_demo_account(settings.demo_seed_file) if settings.demo_enabled else None
    # Demo mode: seed the price cache from a dated snapshot of real AWS prices
    # so pricing works with zero AWS setup (and never invents a number).
    if settings.demo_enabled:
        app.state.pricing.seed_cache_from_snapshot(settings.demo_price_snapshot_file)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    _settings = load_settings()
    uvicorn.run("app.main:app", host=_settings.host, port=_settings.port, reload=True)
