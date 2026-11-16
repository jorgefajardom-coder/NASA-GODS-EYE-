"""Scientific schedule provenance and immutable ROS request binding controls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

from mge_mission.planning_context import (SCHEMA_VERSION, ContextStore,
    PlanningActivity, PlanningContext, PlanningContextError, context_for_request,
    context_from_wire, context_to_wire, profile_registry_sha256,
    scientific_model_sha256, wire_request_digest, wire_request_payload)


REGISTRY = "a" * 64
MODEL = "mge-science-1.0.0"


def request(kind="HUMAN", **changes):
    value = SimpleNamespace(run_id="run-1", request_id="request-1", agent_id="human_1",
        agent_kind=kind, start=SimpleNamespace(x=2., y=2., z=-2400.),
        goal=SimpleNamespace(x=6., y=2., z=-2399.9),
        return_to=SimpleNamespace(x=2., y=2., z=-2400.), require_return=True,
        mode="FAST", map_version=7, service_time_s=3., time_budget_s=100.,
        energy_budget_wh=20., oxygen_budget_l=8. if kind == "HUMAN" else float("nan"),
        reserve_time_s=10., reserve_wh=2.,
        reserve_oxygen_l=1. if kind == "HUMAN" else float("nan"))
    for name, v in changes.items():
        setattr(value, name, v)
    return value


def context(wire=None):
    return context_for_request(wire or request(), MODEL, REGISTRY,
        (PlanningActivity("inspection-remaining", "inspect", 2.),
         PlanningActivity("wait-remaining", "wait", 1.)))


def resolve(store, wire):
    return store.resolve(wire, expected_model_id=MODEL,
                         expected_profile_registry_sha256=REGISTRY)


def test_context_registration_roundtrip_and_idempotent_ack():
    c = context(); store = ContextStore()
    assert isinstance(c, PlanningContext) and c.schema_version == SCHEMA_VERSION
    decoded = context_from_wire(context_to_wire(c, SimpleNamespace()))
    assert decoded == c
    first, duplicate = store.register(c), store.register(decoded)
    assert (first.accepted, first.reason_code) == (True, "COST_CONTEXT_REGISTERED")
    assert duplicate.accepted and duplicate.reason_code == "COST_CONTEXT_DUPLICATE"
    assert first.context_sha256 == duplicate.context_sha256 == c.digest
    assert resolve(store, request()) is c and len(store) == 1
    assert c.payload()["activities"][0]["phase"] == "AT_GOAL"


def test_ordered_activity_identity_affects_digest_without_changing_duration():
    c = context()
    sample = replace(c, activities=(PlanningActivity("sample", "sample", 3.),))
    reversed_schedule = replace(c, activities=tuple(reversed(c.activities)))
    assert len({c.digest, sample.digest, reversed_schedule.digest}) == 3
    store = ContextStore(); store.register(c)
    result = store.register(sample)
    assert not result.accepted and result.reason_code == "COST_CONTEXT_CONFLICT"
    assert resolve(store, request()) == c


def test_cap_limit_does_not_evict_or_modify_existing_context():
    store = ContextStore(max_entries=1); c = context(); store.register(c)
    new = context(request(request_id="request-2"))
    assert store.register(new).reason_code == "COST_CONTEXT_CAPACITY"
    assert not store.register(new).accepted
    assert store.register(c).accepted and resolve(store, request()) is c


def test_registry_retains_immutable_inputs():
    c = context(); mutable = list(c.activities)
    copied = replace(c, activities=mutable)
    mutable.clear()
    assert len(copied.activities) == 2
    with pytest.raises(FrozenInstanceError):
        copied.model_id = "other"
    with pytest.raises(FrozenInstanceError):
        copied.activities[0].remaining_s = 1


def test_concurrent_identical_registration_has_one_new_record():
    c = context(); store = ContextStore()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(store.register, [c] * 20))
    assert sum(r.reason_code == "COST_CONTEXT_REGISTERED" for r in results) == 1
    assert all(r.accepted and r.context_sha256 == c.digest for r in results)
    assert len(store) == 1


@pytest.mark.parametrize("field,value", [
    ("run_id", "other-run"), ("request_id", "other-request"),
    ("agent_id", "other-agent"), ("map_version", 8)])
def test_wrong_identity_has_no_implicit_context_fallback(field, value):
    store = ContextStore(); store.register(context())
    with pytest.raises(PlanningContextError) as error:
        resolve(store, request(**{field: value}))
    assert error.value.reason_code == "COST_CONTEXT_REQUIRED"


@pytest.mark.parametrize("field", ["service_time_s", "time_budget_s", "energy_budget_wh",
    "oxygen_budget_l", "reserve_time_s", "reserve_wh", "reserve_oxygen_l"])
def test_every_resource_field_is_bound_to_current_request(field):
    store = ContextStore(); store.register(context()); changed = request()
    setattr(changed, field, getattr(changed, field) + 1.)
    with pytest.raises(PlanningContextError) as error:
        resolve(store, changed)
    assert error.value.reason_code == "COST_CONTEXT_REQUEST_MISMATCH"


@pytest.mark.parametrize("field", ["start", "goal", "return_to"])
def test_actual_xyz_changes_invalidate_binding_without_rounding_pose(field):
    original = request(); changed = deepcopy(original)
    getattr(changed, field).z += 1e-8
    assert wire_request_digest(original) != wire_request_digest(changed)
    assert wire_request_payload(changed)[field][2] == getattr(changed, field).z


@pytest.mark.parametrize("field,value", [("mode", "SAFE"), ("require_return", False)])
def test_mode_and_return_policy_are_bound(field, value):
    assert wire_request_digest(request()) != wire_request_digest(request(**{field: value}))


def test_float32_fields_have_canonical_wire_roundtrip():
    original = request(energy_budget_wh=.1)
    rounded = struct.unpack("!f", struct.pack("!f", .1))[0]
    assert wire_request_payload(original)["energy_budget_wh"] == rounded
    assert wire_request_digest(original) == wire_request_digest(request(energy_budget_wh=rounded))


@pytest.mark.parametrize("kind", ["ROVER", "DRONE"])
def test_nonhuman_wire_oxygen_nan_is_absent_in_canonical_json(kind):
    payload = wire_request_payload(request(kind))
    assert payload["oxygen_budget_l"] is payload["reserve_oxygen_l"] is None
    wire_request_digest(request(kind))
    for invalid in (0., None, float("inf")):
        with pytest.raises(PlanningContextError):
            wire_request_digest(request(kind, oxygen_budget_l=invalid))


@pytest.mark.parametrize("field", ["service_time_s", "energy_budget_wh", "oxygen_budget_l"])
@pytest.mark.parametrize("bad", [-1., float("nan"), float("inf"), True])
def test_invalid_resources_fail_before_hashing(field, bad):
    with pytest.raises(PlanningContextError):
        wire_request_digest(request(**{field: bad}))


@pytest.mark.parametrize("changes,reason", [
    ({"schema_version": "other"}, "UNSUPPORTED_COST_CONTEXT"),
    ({"map_version": -1}, "INVALID_COST_CONTEXT"),
    ({"map_version": True}, "INVALID_COST_CONTEXT"),
    ({"request_sha256": "bad"}, "INVALID_COST_CONTEXT"),
    ({"profile_registry_sha256": "x" * 64}, "INVALID_COST_CONTEXT"),
    ({"run_id": " "}, "INVALID_COST_CONTEXT")])
def test_invalid_context_identity_or_digest_is_rejected(changes, reason):
    with pytest.raises(PlanningContextError) as error:
        replace(context(), **changes)
    assert error.value.reason_code == reason


def test_profile_model_and_schedule_are_checked_at_resolution():
    c = context()
    variants = [(replace(c, model_id="different-model"), "COST_CONTEXT_MODEL_MISMATCH"),
        (replace(c, profile_registry_sha256="b" * 64), "COST_CONTEXT_PROFILE_MISMATCH"),
        (replace(c, activities=(PlanningActivity("partial", "inspect", 1.),)), "COST_CONTEXT_DURATION_MISMATCH"),
        (replace(c, model_source_sha256="b" * 64), "COST_CONTEXT_MODEL_SOURCE_MISMATCH")]
    for changed, reason in variants:
        store = ContextStore(); store.register(changed)
        with pytest.raises(PlanningContextError) as error:
            resolve(store, request())
        assert error.value.reason_code == reason


def test_partial_remaining_service_and_wait_are_explicit_not_replayed():
    wire = request(service_time_s=1.25)
    c = context_for_request(wire, MODEL, REGISTRY,
        (PlanningActivity("inspect-remainder", "inspect", .75), PlanningActivity("remaining-wait", "wait", .5)))
    assert sum(a.remaining_s for a in c.activities) == 1.25
    assert [a.activity_id for a in c.activities] == ["inspect-remainder", "remaining-wait"]
    with pytest.raises(PlanningContextError) as error:
        replace(c, activities=(c.activities[0], c.activities[0]))
    assert error.value.reason_code == "DUPLICATE_ACTIVITY"


def test_duration_mismatch_never_receives_a_context_for_request():
    with pytest.raises(PlanningContextError) as error:
        context_for_request(request(), MODEL, REGISTRY, (PlanningActivity("inspect", "inspect", 2.999999),))
    assert error.value.reason_code == "COST_CONTEXT_DURATION_MISMATCH"


def test_invalid_activity_and_wire_arrays_are_rejected():
    for bad in (-1., float("nan"), float("inf"), True):
        with pytest.raises(PlanningContextError):
            PlanningActivity("inspect", "inspect", bad)
    with pytest.raises(PlanningContextError):
        replace(context(), activities=(PlanningActivity("huge-1", "wait", 1e308), PlanningActivity("huge-2", "wait", 1e308)))
    message = context_to_wire(context(), SimpleNamespace())
    message.activity_kinds = []
    with pytest.raises(PlanningContextError):
        context_from_wire(message)


def test_profile_hash_uses_exact_registry_bytes(tmp_path):
    p = tmp_path / "profiles.json"; p.write_bytes(b'{"a":1}\n')
    assert profile_registry_sha256(p) == hashlib.sha256(p.read_bytes()).hexdigest()
    old = profile_registry_sha256(p); p.write_bytes(b'{"a": 1}\n')
    assert profile_registry_sha256(p) != old


def test_kernel_source_identity_is_explicit_in_wire_and_digest():
    from mge_mission import models
    c = context()
    expected = hashlib.sha256(Path(models.__file__).read_bytes()).hexdigest()
    assert scientific_model_sha256() == c.model_source_sha256 == expected
    changed = replace(c, model_source_sha256="c" * 64)
    assert changed.digest != c.digest
    assert context_from_wire(context_to_wire(changed, SimpleNamespace())) == changed
    store = ContextStore(); store.register(c)
    rejected = store.register(changed)
    assert not rejected.accepted and rejected.reason_code == "COST_CONTEXT_CONFLICT"
    wire = request()
    with pytest.raises(PlanningContextError) as error:
        store.resolve(wire, expected_model_id=MODEL, expected_profile_registry_sha256=REGISTRY,
                      expected_model_source_sha256="c" * 64)
    assert error.value.reason_code == "COST_CONTEXT_MODEL_SOURCE_MISMATCH"


def test_missing_or_invalid_kernel_source_identity_is_rejected():
    message = context_to_wire(context(), SimpleNamespace())
    del message.model_source_sha256
    with pytest.raises(PlanningContextError):
        context_from_wire(message)
    with pytest.raises(PlanningContextError):
        replace(context(), model_source_sha256="wrong")
    with pytest.raises(PlanningContextError):
        context_for_request(request(), MODEL, REGISTRY, context().activities, model_source_sha256="")
