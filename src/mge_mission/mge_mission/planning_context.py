"""Immutable scientific planning context for the unchanged PlanRoute request.

AI-assisted implementation; mandatory disclosure is recorded in docs/ai_usage.json.
An accepted context identifies predictions, never completed work or approval.
"""
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from threading import RLock


SCHEMA_VERSION = "mge-planning-cost-context-1.0.0"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_KINDS = {"HUMAN", "ROVER", "DRONE"}
_MODES = {"FAST", "SAFE", "EFFICIENT"}
_FLOAT32_FIELDS = ("service_time_s", "time_budget_s", "energy_budget_wh",
                   "oxygen_budget_l", "reserve_time_s", "reserve_wh", "reserve_oxygen_l")


class PlanningContextError(ValueError):
    """Explicit fail-closed context rejection, suitable for a ROS reason code."""
    def __init__(self, reason_code, detail=""):
        self.reason_code = reason_code
        super().__init__(detail or reason_code)


def _identifier(value, field):
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 512:
        raise PlanningContextError("INVALID_COST_CONTEXT", f"{field} requires a bounded explicit identifier")
    return value


def _hash(value, field):
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise PlanningContextError("INVALID_COST_CONTEXT", f"{field} requires a lowercase SHA-256")
    return value


def _version(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise PlanningContextError("INVALID_COST_CONTEXT", "map_version must be uint32")
    return value


def _finite(value, field, *, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PlanningContextError("INVALID_COST_CONTEXT", f"{field} must be numeric")
    try:
        value = float(value)
    except OverflowError as exc:
        raise PlanningContextError("INVALID_COST_CONTEXT", f"{field} exceeds finite range") from exc
    if not math.isfinite(value) or (nonnegative and value < 0):
        raise PlanningContextError("INVALID_COST_CONTEXT", f"{field} must be finite and nonnegative" if nonnegative else f"{field} must be finite")
    return 0.0 if value == 0 else value


def _float32(value, field):
    value = _finite(value, field, nonnegative=True)
    try:
        rounded = struct.unpack("!f", struct.pack("!f", value))[0]
    except (OverflowError, struct.error) as exc:
        raise PlanningContextError("INVALID_COST_CONTEXT", f"{field} exceeds float32") from exc
    if not math.isfinite(rounded):
        raise PlanningContextError("INVALID_COST_CONTEXT", f"{field} exceeds float32")
    return rounded


def canonical_payload(value):
    """Stable UTF-8 JSON representation; nonfinite values cannot enter a hash."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _digest(value):
    return hashlib.sha256(canonical_payload(value).encode("utf-8")).hexdigest()


def wire_request_payload(message):
    """Bind every PlanRoute input, preserving float64 coordinates exactly.

    Only float32 fields are rounded to their declared wire representation.
    The robot oxygen NaNs become null; NaN is invalid in every other field.
    """
    try:
        result = {name: _identifier(getattr(message, name), name)
                  for name in ("run_id", "request_id", "agent_id")}
        kind = message.agent_kind
        if not isinstance(kind, str) or kind not in _KINDS or not isinstance(message.mode, str) or message.mode not in _MODES:
            raise PlanningContextError("INVALID_COST_CONTEXT", "noncanonical agent kind or route mode")
        if type(message.require_return) is not bool:
            raise PlanningContextError("INVALID_COST_CONTEXT", "require_return must be boolean")
        result.update(agent_kind=kind, mode=message.mode,
                      require_return=message.require_return, map_version=_version(message.map_version))
        for name in ("start", "goal", "return_to"):
            point = getattr(message, name)
            result[name] = [_finite(getattr(point, axis), name+"."+axis) for axis in "xyz"]
        for name in _FLOAT32_FIELDS:
            value = getattr(message, name)
            if name in {"oxygen_budget_l", "reserve_oxygen_l"} and kind != "HUMAN":
                if not isinstance(value, float) or not math.isnan(value):
                    raise PlanningContextError("INVALID_COST_CONTEXT", "nonhuman oxygen must be the wire NaN")
                result[name] = None
            else:
                result[name] = _float32(value, name)
        return result
    except AttributeError as exc:
        raise PlanningContextError("INVALID_COST_CONTEXT", "incomplete PlanRoute request") from exc


def wire_request_digest(message):
    return _digest(wire_request_payload(message))


def profile_registry_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scientific_model_sha256():
    """Fingerprint the scientific kernel's source, independently of its label."""
    from . import models
    try:
        source = Path(models.__file__)
        if source.suffix != ".py":
            raise OSError("scientific model source file is unavailable")
        return hashlib.sha256(source.read_bytes()).hexdigest()
    except (OSError, TypeError) as exc:
        raise PlanningContextError("MODEL_SOURCE_UNAVAILABLE", str(exc)) from exc


@dataclass(frozen=True)
class PlanningActivity:
    """One explicit remaining stationary operation at the route goal."""
    activity_id: str
    kind: str
    remaining_s: float

    def __post_init__(self):
        _identifier(self.activity_id, "activity_id")
        _identifier(self.kind, "activity kind")
        object.__setattr__(self, "remaining_s", _finite(self.remaining_s, "activity duration", nonnegative=True))


@dataclass(frozen=True)
class PlanningContext:
    schema_version: str
    run_id: str
    request_id: str
    agent_id: str
    map_version: int
    request_sha256: str
    model_id: str
    profile_registry_sha256: str
    activities: tuple[PlanningActivity, ...] = ()
    model_source_sha256: str = field(default_factory=scientific_model_sha256)

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION:
            raise PlanningContextError("UNSUPPORTED_COST_CONTEXT", "unsupported context schema")
        for field in ("run_id", "request_id", "agent_id", "model_id"):
            _identifier(getattr(self, field), field)
        _version(self.map_version)
        _hash(self.request_sha256, "request_sha256")
        _hash(self.profile_registry_sha256, "profile_registry_sha256")
        _hash(self.model_source_sha256, "model_source_sha256")
        activities = tuple(self.activities)
        if len(activities) > 256 or any(not isinstance(a, PlanningActivity) for a in activities):
            raise PlanningContextError("INVALID_COST_CONTEXT", "explicit bounded PlanningActivity schedule required")
        if len({a.activity_id for a in activities}) != len(activities):
            raise PlanningContextError("DUPLICATE_ACTIVITY", "activity identities cannot repeat")
        try:
            duration = math.fsum(a.remaining_s for a in activities)
        except OverflowError as exc:
            raise PlanningContextError("INVALID_COST_CONTEXT", "nonfinite total schedule duration") from exc
        if not math.isfinite(duration):
            raise PlanningContextError("INVALID_COST_CONTEXT", "nonfinite total schedule duration")
        object.__setattr__(self, "activities", activities)

    @property
    def key(self):
        return self.run_id, self.request_id, self.agent_id, self.map_version

    @property
    def digest(self):
        return _digest(self.payload())

    def payload(self):
        return {"schema_version": self.schema_version, "run_id": self.run_id,
                "request_id": self.request_id, "agent_id": self.agent_id,
                "map_version": self.map_version, "request_sha256": self.request_sha256,
                "model_id": self.model_id, "model_source_sha256": self.model_source_sha256,
                "profile_registry_sha256": self.profile_registry_sha256,
                "activities": [{"activity_id": a.activity_id, "kind": a.kind,
                                "remaining_s": a.remaining_s, "phase": "AT_GOAL"} for a in self.activities]}


def context_digest(context):
    return context.digest


def context_for_request(wire_request, model_id, registry_hash, activities=(), *, model_source_sha256=None):
    payload = wire_request_payload(wire_request)
    context = PlanningContext(SCHEMA_VERSION, payload["run_id"], payload["request_id"],
        payload["agent_id"], payload["map_version"], _digest(payload), model_id,
        registry_hash, tuple(activities),
        scientific_model_sha256() if model_source_sha256 is None else model_source_sha256)
    _validate_binding(context, payload, model_id, registry_hash, context.model_source_sha256)
    return context


def context_from_wire(message):
    try:
        ids, kinds, durations = tuple(message.activity_ids), tuple(message.activity_kinds), tuple(message.activity_durations_s)
        if not len(ids) == len(kinds) == len(durations):
            raise PlanningContextError("INVALID_COST_CONTEXT", "activity array lengths differ")
        return PlanningContext(message.schema_version, message.run_id, message.request_id,
            message.agent_id, message.map_version, message.request_sha256, message.model_id,
            message.profile_registry_sha256,
            tuple(PlanningActivity(*parts) for parts in zip(ids, kinds, durations)),
            message.model_source_sha256)
    except AttributeError as exc:
        raise PlanningContextError("INVALID_COST_CONTEXT", "incomplete registration request") from exc


def context_to_wire(context, message):
    for name in ("schema_version", "run_id", "request_id", "agent_id", "map_version",
                 "request_sha256", "model_id", "model_source_sha256", "profile_registry_sha256"):
        setattr(message, name, getattr(context, name))
    message.activity_ids = [a.activity_id for a in context.activities]
    message.activity_kinds = [a.kind for a in context.activities]
    message.activity_durations_s = [a.remaining_s for a in context.activities]
    return message


def _validate_binding(context, payload, expected_model_id, expected_profile_registry_sha256,
                      expected_model_source_sha256):
    key = tuple(payload[k] for k in ("run_id", "request_id", "agent_id", "map_version"))
    if context.key != key:
        raise PlanningContextError("COST_CONTEXT_IDENTITY_MISMATCH")
    if context.request_sha256 != _digest(payload):
        raise PlanningContextError("COST_CONTEXT_REQUEST_MISMATCH")
    if context.model_id != expected_model_id:
        raise PlanningContextError("COST_CONTEXT_MODEL_MISMATCH")
    if context.profile_registry_sha256 != expected_profile_registry_sha256:
        raise PlanningContextError("COST_CONTEXT_PROFILE_MISMATCH")
    if context.model_source_sha256 != expected_model_source_sha256:
        raise PlanningContextError("COST_CONTEXT_MODEL_SOURCE_MISMATCH")
    if math.fsum(a.remaining_s for a in context.activities) != payload["service_time_s"]:
        raise PlanningContextError("COST_CONTEXT_DURATION_MISMATCH", "remaining schedule must equal the wire service duration")


@dataclass(frozen=True)
class RegistrationResult:
    accepted: bool
    reason_code: str
    context_sha256: str = ""


class ContextStore:
    """Bounded immutable contexts; capacity/conflicts never evict earlier records."""
    def __init__(self, max_entries=4096):
        if type(max_entries) is not int or max_entries < 1:
            raise ValueError("max_entries must be a positive integer")
        self.max_entries = max_entries
        self._records = {}
        self._lock = RLock()

    def register(self, context):
        if not isinstance(context, PlanningContext):
            raise PlanningContextError("INVALID_COST_CONTEXT", "PlanningContext required")
        with self._lock:
            previous = self._records.get(context.key)
            if previous is not None:
                if previous != context:
                    return RegistrationResult(False, "COST_CONTEXT_CONFLICT")
                return RegistrationResult(True, "COST_CONTEXT_DUPLICATE", previous.digest)
            if len(self._records) >= self.max_entries:
                return RegistrationResult(False, "COST_CONTEXT_CAPACITY")
            self._records[context.key] = context
            return RegistrationResult(True, "COST_CONTEXT_REGISTERED", context.digest)

    def resolve(self, wire_request, *, expected_model_id, expected_profile_registry_sha256,
                expected_model_source_sha256=None):
        payload = wire_request_payload(wire_request)
        key = tuple(payload[k] for k in ("run_id", "request_id", "agent_id", "map_version"))
        with self._lock:
            context = self._records.get(key)
        if context is None:
            raise PlanningContextError("COST_CONTEXT_REQUIRED")
        _validate_binding(context, payload, expected_model_id, expected_profile_registry_sha256,
                          scientific_model_sha256() if expected_model_source_sha256 is None else expected_model_source_sha256)
        return context

    def __len__(self):
        with self._lock:
            return len(self._records)
