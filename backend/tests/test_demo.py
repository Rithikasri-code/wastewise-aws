"""Demo loader tests: the fake account comes entirely from the seed file."""
from __future__ import annotations

import json

import pytest

from app.config import load_settings
from app.demo import load_demo_account
from app.demo.loader import DemoSeedError


def test_loads_shipped_seed():
    account = load_demo_account(load_settings().demo_seed_file)
    assert account.account_id
    assert account.enabled_regions
    # The seed is realistic: it must contain resources of every detector type.
    assert account.ec2_instances
    assert account.ebs_volumes
    assert account.ebs_snapshots
    assert account.elastic_ips
    assert account.rds_instances
    assert account.load_balancers
    assert account.resource_count() > 0


def test_missing_file_raises(tmp_path):
    with pytest.raises(DemoSeedError):
        load_demo_account(tmp_path / "does_not_exist.json")


def test_invalid_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(DemoSeedError):
        load_demo_account(bad)


def test_missing_required_key_raises(tmp_path):
    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps({"enabled_regions": []}), encoding="utf-8")
    with pytest.raises(DemoSeedError):
        load_demo_account(partial)


def test_seed_is_editable_values_flow_through(tmp_path):
    seed = tmp_path / "custom.json"
    seed.write_text(
        json.dumps({"account_id": "999", "enabled_regions": ["ap-south-1"], "ec2_instances": [{"instance_id": "i-1"}]}),
        encoding="utf-8",
    )
    account = load_demo_account(seed)
    assert account.account_id == "999"
    assert account.enabled_regions == ["ap-south-1"]
    assert len(account.ec2_instances) == 1
