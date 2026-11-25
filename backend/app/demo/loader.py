"""Load the fake AWS account from an editable JSON seed file.

No fake values live in code. The entire demo account is described by the seed
file (path from config), so a user can edit it to model any scenario. Detectors
in Phase 2 will read these resources and price them through the real pricing
pipeline. Each resource carries the raw attributes a detector needs (metrics,
attachment state, age) so detectors stay config-driven and testable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class DemoSeedError(ValueError):
    """Raised when the demo seed file is missing or malformed."""


@dataclass
class DemoAccount:
    account_id: str
    enabled_regions: list[str]
    ec2_instances: list[dict[str, Any]] = field(default_factory=list)
    ebs_volumes: list[dict[str, Any]] = field(default_factory=list)
    ebs_snapshots: list[dict[str, Any]] = field(default_factory=list)
    elastic_ips: list[dict[str, Any]] = field(default_factory=list)
    rds_instances: list[dict[str, Any]] = field(default_factory=list)
    load_balancers: list[dict[str, Any]] = field(default_factory=list)

    def resource_count(self) -> int:
        return (
            len(self.ec2_instances)
            + len(self.ebs_volumes)
            + len(self.ebs_snapshots)
            + len(self.elastic_ips)
            + len(self.rds_instances)
            + len(self.load_balancers)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "enabled_regions": self.enabled_regions,
            "resource_count": self.resource_count(),
            "ec2_instances": self.ec2_instances,
            "ebs_volumes": self.ebs_volumes,
            "ebs_snapshots": self.ebs_snapshots,
            "elastic_ips": self.elastic_ips,
            "rds_instances": self.rds_instances,
            "load_balancers": self.load_balancers,
        }


def load_demo_account(seed_path: Path) -> DemoAccount:
    path = Path(seed_path)
    if not path.exists():
        raise DemoSeedError(f"Demo seed file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:  # surface a clear, plain message
            raise DemoSeedError(f"Demo seed file is not valid JSON: {exc}") from exc

    try:
        return DemoAccount(
            account_id=str(data["account_id"]),
            enabled_regions=list(data["enabled_regions"]),
            ec2_instances=list(data.get("ec2_instances", [])),
            ebs_volumes=list(data.get("ebs_volumes", [])),
            ebs_snapshots=list(data.get("ebs_snapshots", [])),
            elastic_ips=list(data.get("elastic_ips", [])),
            rds_instances=list(data.get("rds_instances", [])),
            load_balancers=list(data.get("load_balancers", [])),
        )
    except KeyError as exc:
        raise DemoSeedError(f"Demo seed file is missing required key: {exc}") from exc
