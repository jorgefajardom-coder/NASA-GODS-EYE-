"""Source-traced simulation estimates; profile approval is a separate decision.

This module has no evaluator, terrain file, ROS, or hidden task input. Resource
estimates describe the declared engineering model and never certify EVA safety.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


MODEL_ID = "mge-science-1.0.0"
OXYGEN_MOLAR_MASS_KG_MOL = 0.0319988
OXYGEN_IDEAL_MOLAR_VOLUME_L = 22.41396954
OXYGEN_REFERENCE_KG_H = 0.086
OXYGEN_REFERENCE_POWER_W = 295.0
OXYGEN_L_PER_WH = (OXYGEN_REFERENCE_KG_H / OXYGEN_MOLAR_MASS_KG_MOL
                   * OXYGEN_IDEAL_MOLAR_VOLUME_L / OXYGEN_REFERENCE_POWER_W)


def _number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return float(value)


@dataclass(frozen=True)
class AssumptionRecord:
    parameter: str
    value: float
    unit: str
    origin: str
    source_url: str
    sensitivity_min: float
    sensitivity_max: float
    owner: str = "David"
    approval_status: str = "proposed"
    source_locator: str = ""
    note: str = ""

    def __post_init__(self):
        if not self.parameter or not self.unit or not self.owner:
            raise ValueError("parameter, unit, and owner are required")
        if self.origin not in {"source", "source_analog", "derived", "engineering_assumption"}:
            raise ValueError("unknown assumption origin")
        value = _number(self.value, self.parameter)
        low = _number(self.sensitivity_min, "sensitivity_min")
        high = _number(self.sensitivity_max, "sensitivity_max")
        if not low <= value <= high:
            raise ValueError("sensitivity range must contain the parameter value")
        if self.origin != "engineering_assumption" and not self.source_url.startswith("https://"):
            raise ValueError("sourced and derived parameters require an HTTPS source")
        if self.approval_status not in {"proposed", "illustrative", "approved"}:
            raise ValueError("unknown approval status")


@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    kind: str
    capabilities: tuple[str, ...]
    parameters: dict[str, float]
    activity_power_w: dict[str, float]
    approval_status: str = "proposed"
    model_id: str = MODEL_ID

    def __post_init__(self):
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("agent_id is required")
        if self.kind not in {"human", "rover", "drone"}:
            raise ValueError("kind must be lowercase human, rover, or drone")
        if isinstance(self.capabilities, str):
            raise ValueError("capabilities must be a sequence, not a string")
        capabilities = tuple(self.capabilities)
        if not capabilities or any(not isinstance(x, str) or not x for x in capabilities):
            raise ValueError("capabilities must contain nonempty strings")
        if len(set(capabilities)) != len(capabilities):
            raise ValueError("capabilities must be unique")
        if self.approval_status not in {"proposed", "illustrative", "approved"}:
            raise ValueError("unknown approval status")
        if self.model_id != MODEL_ID:
            raise ValueError("unsupported resource model version")
        params = {key: _number(value, key) for key, value in self.parameters.items()}
        powers = {key: _number(value, key) for key, value in self.activity_power_w.items()}
        if any(not isinstance(key, str) or not key for key in (*params, *powers)):
            raise ValueError("parameter and activity names must be nonempty strings")
        common = {"max_slope_deg", "max_step_m", "radius_m", "localization_error_m", "max_sigma_m"}
        required = {
            "human": {"body_mass_kg", "suit_mass_kg", "speed_m_s", "slope_slowdown", "climb_efficiency", "gravity_m_s2"},
            "rover": {"mass_kg", "speed_m_s", "rolling_resistance", "slip", "drive_efficiency", "auxiliary_power_w", "gravity_m_s2"},
            "drone": {"mass_kg", "speed_m_s", "vertical_speed_m_s", "climb_efficiency", "gravity_m_s2"},
        }[self.kind] | common
        missing = required - params.keys()
        if missing:
            raise ValueError(f"missing {self.kind} parameters: {', '.join(sorted(missing))}")
        for name in ("speed_m_s", "radius_m"):
            _number(params[name], name, positive=True)
        if params["max_slope_deg"] > 90:
            raise ValueError("maximum slope must not exceed 90 degrees")
        if "max_downhill_slope_deg" in params and params["max_downhill_slope_deg"] > 90:
            raise ValueError("maximum downhill slope must not exceed 90 degrees")
        for name in ("climb_efficiency", "drive_efficiency"):
            if name in params and not 0 < params[name] <= 1:
                raise ValueError(f"{name} must be in (0, 1]")
        if self.kind == "rover" and not 0 <= params["slip"] < 1:
            raise ValueError("slip must be in [0, 1)")
        for name in ("body_mass_kg", "mass_kg", "vertical_speed_m_s", "gravity_m_s2"):
            if name in params:
                _number(params[name], name, positive=True)
        required_activities = {
            "human": {"walk", "wait", "inspect", "sample"},
            "rover": {"wait", "inspect"},
            "drone": {"ground_wait", "translate", "ascent", "descent", "hover", "observe"},
        }[self.kind]
        if required_activities - powers.keys():
            raise ValueError("profile lacks required activity powers")
        if self.kind == "human":
            _number(powers["walk"], "walking power", positive=True)
            _number(params.get("oxygen_scale", 1.0), "oxygen_scale", positive=True)
        elif self.kind == "rover":
            _number(params["auxiliary_power_w"], "auxiliary_power_w", positive=True)
        else:
            _number(powers["translate"], "translation power", positive=True)
        if self.kind != "human" and any("oxygen" in key.lower() for key in params):
            raise ValueError("robots must not include human oxygen parameters")
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "parameters", MappingProxyType(params))
        object.__setattr__(self, "activity_power_w", MappingProxyType(powers))


@dataclass(frozen=True)
class CostEstimate:
    time_s: float
    energy_wh: float
    oxygen_l: float | None

    def __post_init__(self):
        _number(self.time_s, "time_s")
        _number(self.energy_wh, "energy_wh")
        if self.oxygen_l is not None:
            _number(self.oxygen_l, "oxygen_l")


def _point(value):
    try:
        point = tuple(value)
    except TypeError as exc:
        raise ValueError("ENU point must contain three finite coordinates") from exc
    if len(point) != 3:
        raise ValueError("ENU point must contain three finite coordinates")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in point):
        raise ValueError("ENU point must contain three finite coordinates")
    return point


def _cost(profile, time_s, energy_wh):
    oxygen = (energy_wh * OXYGEN_L_PER_WH * profile.parameters.get("oxygen_scale", 1.0)
              if profile.kind == "human" else None)
    return CostEstimate(time_s, energy_wh, oxygen)


def estimate_segment(profile: AgentProfile, start_enu, end_enu) -> CostEstimate:
    """Estimate one directed edge; no rounding, regenerative credit, or approval.

    Grade limits are enforced. Step, footprint, uncertainty, and obstacle checks
    require the public map and remain planner responsibilities.
    """
    start, end = _point(start_enu), _point(end_enu)
    dx, dy, dz = (b - a for a, b in zip(start, end))
    horizontal = math.hypot(dx, dy)
    length = math.hypot(horizontal, dz)
    if length == 0:
        return _cost(profile, 0.0, 0.0)
    params, powers = profile.parameters, profile.activity_power_w
    if profile.kind == "drone":
        time = max(horizontal / params["speed_m_s"], abs(dz) / params["vertical_speed_m_s"])
        power = powers["translate"] if horizontal > 0 else powers["ascent"] if dz > 0 else powers["descent"]
        climb_j = params["mass_kg"] * params["gravity_m_s2"] * max(dz, 0.0) / params["climb_efficiency"]
        return _cost(profile, time, (power * time + climb_j) / 3600)
    if horizontal == 0:
        raise ValueError("ground agents cannot traverse a vertical-only segment")
    slope = math.degrees(math.atan2(abs(dz), horizontal))
    slope_limit = params.get("max_downhill_slope_deg", params["max_slope_deg"]) if dz < 0 else params["max_slope_deg"]
    if slope > slope_limit + 1e-12:
        raise ValueError("segment exceeds the proposed slope limit")
    if profile.kind == "human":
        time = horizontal * (1 + params["slope_slowdown"] * abs(dz) / horizontal) / params["speed_m_s"]
        climb_j = ((params["body_mass_kg"] + params["suit_mass_kg"]) * params["gravity_m_s2"]
                   * max(dz, 0.0) / params["climb_efficiency"])
        return _cost(profile, time, (powers["walk"] * time + climb_j) / 3600)
    slip_factor = 1 - params["slip"]
    time = length / (params["speed_m_s"] * slip_factor)
    theta = math.atan2(dz, horizontal)
    force = params["mass_kg"] * params["gravity_m_s2"] * (
        params["rolling_resistance"] * math.cos(theta) + math.sin(theta))
    drive_j = max(0.0, force) * length / (params["drive_efficiency"] * slip_factor)
    return _cost(profile, time, (params["auxiliary_power_w"] * time + drive_j) / 3600)


def estimate_activity(profile: AgentProfile, activity: str, duration_s: float) -> CostEstimate:
    """Integrate one explicit service/wait power; callers count it exactly once."""
    duration = _number(duration_s, "duration_s")
    aliases = {"idle": "ground_wait" if profile.kind == "drone" else "wait", "light": "inspect", "survey": "observe"}
    key = aliases.get(activity, activity)
    if profile.kind == "drone" and key == "wait":
        key = "ground_wait"
    if key not in profile.activity_power_w:
        raise ValueError(f"unsupported {profile.kind} activity: {activity}")
    return _cost(profile, duration, profile.activity_power_w[key] * duration / 3600)


def load_profiles(path) -> dict[str, AgentProfile]:
    """Load immutable profiles without promoting proposed assumptions to approval."""
    source = Path(path)
    if source.suffix.lower() in {".yaml", ".yml"}:
        import yaml
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
    else:
        data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != "1.0.0":
        raise ValueError("profile registry requires schema_version 1.0.0")
    if data.get("model_id", MODEL_ID) != MODEL_ID:
        raise ValueError("unsupported resource model version")
    values = data.get("profiles")
    if not isinstance(values, dict) or not values:
        raise ValueError("profiles must map agent IDs to nonempty profile records")
    result = {}
    for agent_id, record in values.items():
        if not isinstance(record, dict) or record.get("agent_id", agent_id) != agent_id:
            raise ValueError("profile key and agent_id must agree")
        result[agent_id] = AgentProfile(
            agent_id=agent_id, kind=record["kind"], capabilities=tuple(record["capabilities"]),
            parameters=record["parameters"], activity_power_w=record["activity_power_w"],
            approval_status=record.get("approval_status", data.get("status", "proposed")),
            model_id=record.get("model_id", data.get("model_id", MODEL_ID)))
    for record in data.get("assumptions", []):
        AssumptionRecord(**record)
    return result


def export_planner_profiles(profiles: Mapping[str, AgentProfile]) -> dict:
    """Project into current MotionProfile fields; this is not model agreement.

    The current planner uses a simpler per-distance model and fixed O2 rate.
    Mission must independently audit the complete itinerary with this module.
    """
    if not profiles or any(key != profile.agent_id for key, profile in profiles.items()):
        raise ValueError("profiles must be nonempty and keyed by agent_id")
    projected = {}
    for agent_id, profile in profiles.items():
        p, a = profile.parameters, profile.activity_power_w
        speed = p["speed_m_s"]
        up_time = down_time = up_energy = 0.0
        oxygen = None
        if profile.kind == "human":
            base_j_m = a["walk"] / speed
            up_time = down_time = p["slope_slowdown"]
            up_energy = up_time + (p["body_mass_kg"] + p["suit_mass_kg"]) * p["gravity_m_s2"] / (p["climb_efficiency"] * base_j_m)
            grade = math.tan(math.radians(min(p["max_slope_deg"], 89.999)))
            max_climb_w = ((p["body_mass_kg"] + p["suit_mass_kg"]) * p["gravity_m_s2"]
                           * speed * grade / (p["climb_efficiency"] * (1 + up_time * grade)))
            oxygen = (max(a["walk"] + max_climb_w, *a.values()) * OXYGEN_L_PER_WH
                      * p.get("oxygen_scale", 1.0) / 3600)
        elif profile.kind == "rover":
            speed *= 1 - p["slip"]
            traction_j_m = p["mass_kg"] * p["gravity_m_s2"] / (p["drive_efficiency"] * (1 - p["slip"]))
            base_j_m = p["auxiliary_power_w"] / speed + traction_j_m * p["rolling_resistance"]
            up_energy = traction_j_m / base_j_m
        else:
            base_j_m = a["translate"] / speed
            up_time = down_time = speed / p["vertical_speed_m_s"]
            up_energy = up_time + p["mass_kg"] * p["gravity_m_s2"] / (p["climb_efficiency"] * base_j_m)
        projected[agent_id] = dict(
            agent_kind=profile.kind, speed_m_s=speed, max_slope_deg=p["max_slope_deg"],
            max_step_m=p["max_step_m"], radius_m=p["radius_m"], localization_error_m=p["localization_error_m"],
            energy_wh_per_m=base_j_m / 3600, oxygen_l_per_s=oxygen,
            uphill_time_factor=up_time, downhill_time_factor=down_time,
            uphill_energy_factor=up_energy, downhill_energy_factor=0.0,
            service_power_w=max(a.values()), max_downhill_slope_deg=p.get("max_downhill_slope_deg", p["max_slope_deg"]),
            max_sigma_m=p["max_sigma_m"])
    illustrative = all(profile.approval_status == "illustrative" for profile in profiles.values())
    return {
        "schema_version": "1.0.0", "model_id": MODEL_ID,
        "status": "illustrative" if illustrative else "pending_model_agreement",
        "profiles": projected,
        "approximation": {
            "exact_science_model": False,
            "reason": "Current planner has per-distance energy and constant human oxygen; mission audits full activity/grade costs independently.",
            "human_oxygen": "Maximum admitted climb/activity rate, not a constant physiological measurement.",
            "drone": "Ground-grid projection; it cannot verify flight clearance or 3D collision avoidance.",
            "approval": "Scientific profile approval does not approve this projection."}}
