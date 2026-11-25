"""Configuration loader - the single place that reads config files and env vars.

Design rule for the whole project: no prices, thresholds, regions, currency,
paths, or product names are written directly in Python. They are read here from
config/app.yaml, config/rules.yaml, and config/language.en.json, and any value
can be overridden by an environment variable (see .env.example).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

# backend/ directory: app/config.py -> app -> backend
BASE_DIR = Path(__file__).resolve().parent.parent
APP_YAML_PATH = BASE_DIR / "config" / "app.yaml"

# Load .env from the repo root if present. Real secrets (AWS keys) are never
# committed; only paths/profile names and non-secret overrides live here.
load_dotenv(BASE_DIR.parent / ".env")


def _resolve(path_str: str) -> Path:
    """Resolve a configured path relative to backend/ unless it is absolute."""
    p = Path(path_str)
    return p if p.is_absolute() else (BASE_DIR / p)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _as_int(raw: Optional[str], fallback: int) -> int:
    try:
        return int(raw) if raw not in (None, "") else fallback
    except (TypeError, ValueError):
        return fallback


@dataclass(frozen=True)
class Settings:
    """Typed, validated view of all runtime configuration."""

    host: str
    port: int
    database_path: Path
    cors_origins: list[str]
    language_file: Path
    rules_file: Path
    demo_seed_file: Path
    demo_price_snapshot_file: Path
    demo_enabled: bool
    pricing_api_region: str
    cache_ttl_seconds: int
    hours_per_month: int
    default_currency: str
    aws_profile: Optional[str]
    raw_app: dict[str, Any] = field(default_factory=dict, repr=False)

    def monthly_from_hourly(self, hourly: float) -> float:
        """Convert an hourly on-demand price to a monthly estimate.

        This is always an estimate; callers must label it as such in the UI.
        """
        return hourly * self.hours_per_month


class ConfigError(RuntimeError):
    """A required configuration value is missing from config/app.yaml."""


def _require(section: dict[str, Any], key: str) -> Any:
    if key not in section or section[key] in (None, ""):
        raise ConfigError(f"Missing required config key '{key}' in config/app.yaml")
    return section[key]


def load_settings() -> Settings:
    """Read app.yaml, apply env overrides, and return typed settings.

    Every value comes from config/app.yaml (or an env override). There are no
    hardcoded regions, currencies, ports, hosts, or paths in this function -
    if a required key is absent it raises ConfigError instead of inventing one.
    """
    data = _load_yaml(APP_YAML_PATH)
    app = data.get("app") or {}
    pricing = data.get("pricing") or {}
    demo = data.get("demo") or {}

    def env_or(section: dict[str, Any], key: str, env: str) -> str:
        override = os.getenv(env)
        return override if override is not None else str(_require(section, key))

    cors_env = os.getenv("WASTWISE_CORS_ORIGINS")
    cors_origins = (
        [o.strip() for o in cors_env.split(",") if o.strip()]
        if cors_env
        else list(_require(app, "cors_origins"))
    )

    demo_env = os.getenv("WASTWISE_DEMO")
    demo_enabled = (
        demo_env.lower() in ("1", "true", "yes")
        if demo_env is not None
        else bool(_require(demo, "enabled"))
    )

    return Settings(
        host=env_or(app, "host", "WASTWISE_HOST"),
        port=_as_int(os.getenv("WASTWISE_PORT"), int(_require(app, "port"))),
        database_path=_resolve(env_or(app, "database_path", "WASTWISE_DATABASE_PATH")),
        cors_origins=cors_origins,
        language_file=_resolve(env_or(app, "language_file", "WASTWISE_LANGUAGE_FILE")),
        rules_file=_resolve(env_or(app, "rules_file", "WASTWISE_RULES_FILE")),
        demo_seed_file=_resolve(env_or(app, "demo_seed_file", "WASTWISE_DEMO_SEED_FILE")),
        demo_price_snapshot_file=_resolve(env_or(demo, "price_snapshot_file", "WASTWISE_PRICE_SNAPSHOT_FILE")),
        demo_enabled=demo_enabled,
        pricing_api_region=env_or(pricing, "pricing_api_region", "WASTWISE_PRICING_API_REGION"),
        cache_ttl_seconds=_as_int(os.getenv("WASTWISE_CACHE_TTL_SECONDS"), int(_require(pricing, "cache_ttl_seconds"))),
        hours_per_month=_as_int(os.getenv("WASTWISE_HOURS_PER_MONTH"), int(_require(pricing, "hours_per_month"))),
        default_currency=env_or(pricing, "default_currency", "WASTWISE_CURRENCY"),
        aws_profile=os.getenv("AWS_PROFILE"),
        raw_app=data,
    )


def load_rules(settings: Settings) -> dict[str, Any]:
    """Load detector thresholds from rules.yaml."""
    return _load_yaml(settings.rules_file)


def load_language(settings: Settings) -> dict[str, Any]:
    """Load all on-screen text and branding from the language file."""
    with settings.language_file.open("r", encoding="utf-8") as fh:
        import json

        return json.load(fh)
