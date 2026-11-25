"""Config loader tests: values come from files, env overrides work, and no
value the spec forbids hardcoding is invented in code.
"""
from __future__ import annotations

from app.config import load_language, load_rules, load_settings


def test_settings_load_from_yaml():
    s = load_settings()
    # These come from config/app.yaml, not from code.
    assert s.hours_per_month > 0
    assert s.cache_ttl_seconds > 0
    assert s.default_currency
    assert s.pricing_api_region


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("WASTWISE_CURRENCY", "EUR")
    monkeypatch.setenv("WASTWISE_HOURS_PER_MONTH", "100")
    s = load_settings()
    assert s.default_currency == "EUR"
    assert s.hours_per_month == 100


def test_monthly_from_hourly_is_estimate_math():
    s = load_settings()
    assert s.monthly_from_hourly(1.0) == float(s.hours_per_month)


def test_rules_have_all_detectors():
    rules = load_rules(load_settings())
    for key in [
        "idle_ec2",
        "unattached_ebs_volume",
        "old_ebs_snapshot",
        "unattached_eip",
        "oversized_rds",
        "idle_load_balancer",
    ]:
        assert key in rules, f"missing detector config: {key}"


def test_language_has_branding():
    lang = load_language(load_settings())
    assert lang["branding"]["name"]
    assert lang["branding"]["tagline"]
