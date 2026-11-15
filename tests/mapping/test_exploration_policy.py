"""Policy identity and uncertainty are explicit inputs, not approval flags."""
import hashlib
import json
from pathlib import Path

import pytest

from mge_mapping.policy import load_knowledge_policy

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/exploration_policy.illustrative.json"


def test_loaded_policy_binds_exact_bytes_and_keeps_limits_immutable():
    policy = load_knowledge_policy(POLICY)
    assert policy.allow_estimated
    assert policy.sha256 == hashlib.sha256(POLICY.read_bytes()).hexdigest()
    assert policy.sha256 in policy.source_record
    assert "candidate-only" in policy.source_record
    assert policy.limits["human"]["max_sigma_m"] == 3
    with pytest.raises(TypeError):
        policy.limits["human"]["max_sigma_m"] = 0


@pytest.mark.parametrize("change", [
    {"status": "approved"}, {"mode": "all_free"}, {"policy_id": ""},
    {"schema_version": "2.0.0"}, {"meaning": ""}, {"unexpected": True},
    {"limits": {}},
])
def test_unsupported_or_implicit_policy_is_refused(tmp_path, change):
    data = json.loads(POLICY.read_text()) | change
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_knowledge_policy(path)


@pytest.mark.parametrize("value", [0, -1, True, float("inf"), float("nan")])
def test_uncertainty_gate_cannot_be_disabled_by_invalid_threshold(tmp_path, value):
    data = json.loads(POLICY.read_text())
    data["limits"]["human"]["max_sigma_m"] = value
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_knowledge_policy(path)
