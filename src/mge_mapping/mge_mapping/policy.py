"""Explicit, fingerprinted policy for proposing routes on public estimates.

This configures candidate-map admissibility, never execution authorization or
scientific profile approval. The planner independently applies its own profile.
"""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType


POLICY_SCHEMA = "mge-exploration-policy-1.0.0"
KINDS = {"human", "rover", "drone"}


@dataclass(frozen=True)
class KnowledgePolicy:
    policy_id: str
    mode: str
    limits: dict
    sha256: str

    @property
    def allow_estimated(self):
        return self.mode == "estimated_or_observed"

    @property
    def source_record(self):
        return (f"planning-policy {self.policy_id} [{POLICY_SCHEMA}, "
                f"{self.mode}, illustrative candidate-only, sha256={self.sha256}]")


def load_knowledge_policy(path: str | Path) -> KnowledgePolicy:
    """Load one immutable illustrative policy; reject incomplete/unknown input."""
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or set(data) != {
            "schema_version", "policy_id", "status", "mode", "limits", "meaning"}:
        raise ValueError("exploration policy has missing or unsupported fields")
    if data["schema_version"] != POLICY_SCHEMA or data["status"] != "illustrative":
        raise ValueError("only explicitly illustrative exploration policies are supported")
    if not isinstance(data["policy_id"], str) or not data["policy_id"].strip():
        raise ValueError("exploration policy_id is required")
    if data["mode"] not in {"observed_only", "estimated_or_observed"}:
        raise ValueError("unsupported exploration knowledge mode")
    if not isinstance(data["meaning"], str) or not data["meaning"].strip():
        raise ValueError("exploration policy must explain candidate-only meaning")
    limits = data["limits"]
    if not isinstance(limits, dict) or set(limits) != KINDS:
        raise ValueError("exploration policy requires explicit limits for all three kinds")
    frozen = {}
    for kind, values in limits.items():
        if not isinstance(values, dict) or set(values) != {"max_sigma_m", "max_slope_deg"}:
            raise ValueError(f"invalid exploration limits for {kind}")
        for name, value in values.items():
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value <= 0):
                raise ValueError(f"{kind}.{name} must be positive and finite")
        if values["max_slope_deg"] > 90:
            raise ValueError(f"{kind} slope exceeds 90 degrees")
        frozen[kind] = MappingProxyType(dict(values))
    return KnowledgePolicy(data["policy_id"], data["mode"], MappingProxyType(frozen),
                           hashlib.sha256(raw).hexdigest())
