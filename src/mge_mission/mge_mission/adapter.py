"""Strict ROS-boundary helpers; importing this module never requires ROS.

The core owns decisions. These functions validate representation and translate
the canonical ICD fields without pretending that a route proves execution.
"""

from math import isfinite, isnan
from struct import pack, unpack


WIRE_KINDS = {"HUMAN": "human", "ROVER": "rover", "DRONE": "drone"}
WIRE_MODES = {"IDLE", "MOVING", "OBSERVING", "WORKING", "RETURNING", "HALTED"}
ROUTE_MODES = {"FAST", "SAFE", "EFFICIENT"}
ROUTE_STATUSES = {"FEASIBLE", "UNKNOWN", "NO_PATH", "INSUFFICIENT_BUDGET",
                  "STALE_MAP", "ERROR"}


def finite_number(value, field, *, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if not isfinite(result) or (nonnegative and result < 0):
        raise ValueError(f"{field} must be finite" + (" and nonnegative" if nonnegative else ""))
    return result


def float32(value, field, *, oxygen_na=False):
    """Round to ROS float32, refusing overflow or accidental nonfinite values."""
    if value is None and oxygen_na:
        return float("nan")
    result = finite_number(value, field)
    try:
        result = unpack("!f", pack("!f", result))[0]
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{field} exceeds float32") from exc
    if not isfinite(result):
        raise ValueError(f"{field} exceeds float32")
    return result


def oxygen_from_wire(value, kind, field):
    if kind == "human":
        return finite_number(value, field, nonnegative=True)
    if kind not in {"rover", "drone"}:
        raise ValueError("unknown agent kind")
    if not isinstance(value, float) or not isnan(value):
        raise ValueError(f"{field} must be NaN for non-human agents")
    return None


def unavailable_number_from_wire(value, field):
    """NaN denotes an unavailable failure metric, never a zero measurement."""
    if isinstance(value, float) and isnan(value):
        return None
    return finite_number(value, field, nonnegative=True)


def kind_from_wire(value):
    try:
        return WIRE_KINDS[value]
    except (KeyError, TypeError) as exc:
        raise ValueError("agent_kind must use a canonical uppercase kind") from exc


def kind_to_wire(value):
    if value not in WIRE_KINDS.values():
        raise ValueError("unknown internal agent kind")
    return value.upper()


def stamp_seconds(stamp):
    if type(stamp.sec) is not int or type(stamp.nanosec) is not int:
        raise ValueError("ROS stamp fields must be integers")
    if stamp.sec < 0 or not 0 <= stamp.nanosec < 1_000_000_000:
        raise ValueError("invalid ROS stamp")
    return stamp.sec + stamp.nanosec / 1_000_000_000


def validate_header(message, run_id, now_s):
    if message.run_id != run_id:
        raise ValueError("message belongs to another run")
    if message.header.frame_id != "map":
        raise ValueError("message frame must be map")
    stamp = stamp_seconds(message.header.stamp)
    if stamp > finite_number(now_s, "simulation time", nonnegative=True) + 1e-6:
        raise ValueError("message stamp is ahead of simulation time")
    return stamp


def point_values(point):
    return tuple(finite_number(getattr(point, axis), f"point.{axis}") for axis in "xyz")


def point_to_wire(point, factory):
    result = factory()
    for axis in "xyz":
        setattr(result, axis, finite_number(getattr(point, axis), f"point.{axis}"))
    return result


def set_header(message, run_id, stamp):
    message.header.frame_id = "map"
    message.header.stamp = stamp
    if hasattr(message, "run_id"):
        message.run_id = run_id
    return message


def _point_from_wire(value):
    from .types import Point
    return Point(*point_values(value))


def goal_from_wire(message, run_id, *, primary_kind="human"):
    from .types import GoalRequest
    if primary_kind != "human":
        raise ValueError("the primary mission agent must be human")
    if message.run_id and message.run_id != run_id:
        raise ValueError("goal belongs to another run")
    if message.mode not in ROUTE_MODES:
        raise ValueError("unknown route mode")
    return GoalRequest(
        request_id=message.request_id, run_id=message.run_id or run_id,
        primary_agent_id=message.primary_agent_id, base=_point_from_wire(message.base),
        goal=_point_from_wire(message.goal), mode=message.mode,
        **{name: finite_number(getattr(message, name), name, nonnegative=True)
           for name in ("time_budget_s", "energy_budget_wh", "oxygen_budget_l",
                        "reserve_time_s", "reserve_wh", "reserve_oxygen_l")},
    )


def goal_fingerprint(message, run_id):
    """Canonical semantic request key, independent of CDR padding bytes.

    Invalid nonfinite numbers also have stable keys so a rejected request keeps
    its first answer. Validation remains the responsibility of goal_from_wire.
    """
    def number_key(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return (type(value).__name__, repr(value))
        number = float(value)
        if number == 0:
            number = 0.0  # Signed zero does not change goal or budget semantics.
        return ("number", number.hex())

    return (
        message.run_id or run_id, message.primary_agent_id,
        tuple(number_key(getattr(message.base, axis)) for axis in "xyz"),
        tuple(number_key(getattr(message.goal, axis)) for axis in "xyz"), message.mode,
        tuple(number_key(getattr(message, name)) for name in (
            "time_budget_s", "energy_budget_wh", "oxygen_budget_l",
            "reserve_time_s", "reserve_wh", "reserve_oxygen_l")),
    )


def agent_from_wire(message, run_id, now_s):
    from .types import AgentSnapshot
    stamp = validate_header(message, run_id, now_s)
    kind = kind_from_wire(message.agent_kind)
    if message.mode not in WIRE_MODES:
        raise ValueError("unknown agent mode")
    confidence = finite_number(message.confidence, "confidence", nonnegative=True)
    if confidence > 1:
        raise ValueError("confidence must be in [0, 1]")
    # Validate received geometry even though the mission core only uses position.
    for axis in "xyzw":
        finite_number(getattr(message.pose.orientation, axis), f"orientation.{axis}")
    for vector in (message.velocity.linear, message.velocity.angular):
        point_values(vector)
    return AgentSnapshot(
        run_id=message.run_id, agent_id=message.agent_id, kind=kind,
        position=_point_from_wire(message.pose.position), mode=message.mode,
        timestamp_sim_s=stamp, confidence=confidence,
        time_remaining_s=finite_number(message.time_remaining_s, "time_remaining_s", nonnegative=True),
        energy_remaining_wh=finite_number(message.energy_remaining_wh, "energy_remaining_wh", nonnegative=True),
        oxygen_remaining_l=oxygen_from_wire(message.oxygen_remaining_l, kind, "oxygen_remaining_l"),
    )


def decision_from_wire(message, run_id, now_s, *, kind):
    from .types import RouteDecision
    validate_header(message, run_id, now_s)
    if message.status not in ROUTE_STATUSES or message.mode not in ROUTE_MODES:
        raise ValueError("unknown route status or mode")
    if type(message.map_version_used) is not int or not 0 <= message.map_version_used <= 0xFFFFFFFF:
        raise ValueError("invalid map version")
    feasible = message.status == "FEASIBLE"
    if not feasible and (message.route_id or message.outbound_path or message.return_path):
        raise ValueError("a failed planning decision must not contain an active route")
    convert_number = (lambda value, name: finite_number(value, name, nonnegative=True)) if feasible else unavailable_number_from_wire
    values = {name: convert_number(getattr(message, name), name)
              for name in ("travel_time_s", "energy_est_wh", "min_clearance_m",
                           "reserve_time_s", "reserve_wh")}
    oxygen = {}
    for name in ("oxygen_est_l", "reserve_oxygen_l"):
        oxygen[name] = (unavailable_number_from_wire(getattr(message, name), name)
                        if not feasible and kind == "human"
                        else oxygen_from_wire(getattr(message, name), kind, name))
    return RouteDecision(
        run_id=message.run_id, request_id=message.request_id, route_id=message.route_id,
        agent_id=message.agent_id, mode=message.mode,
        map_version_used=message.map_version_used, status=message.status,
        reason_code=message.reason_code, detail=message.detail,
        outbound_path=tuple(_point_from_wire(point) for point in message.outbound_path),
        return_path=tuple(_point_from_wire(point) for point in message.return_path),
        **oxygen, **values,
    )


def plan_to_wire(plan, message, point_factory):
    for name in ("run_id", "request_id", "agent_id", "require_return", "mode", "map_version"):
        setattr(message, name, getattr(plan, name))
    # PlanRequest mirrors the canonical service; AgentSnapshot/Profile use lowercase.
    kind = kind_from_wire(plan.agent_kind)
    message.agent_kind = kind_to_wire(kind)
    for name in ("start", "goal", "return_to"):
        setattr(message, name, point_to_wire(getattr(plan, name), point_factory))
    for name in ("service_time_s", "time_budget_s", "energy_budget_wh",
                 "reserve_time_s", "reserve_wh"):
        setattr(message, name, float32(getattr(plan, name), name))
    for name in ("oxygen_budget_l", "reserve_oxygen_l"):
        setattr(message, name, float32(getattr(plan, name), name, oxygen_na=kind != "human"))
    return message


def decision_to_wire(decision, message, stamp, point_factory):
    set_header(message, decision.run_id, stamp)
    for name in ("request_id", "route_id", "agent_id", "mode", "map_version_used",
                 "status", "reason_code", "detail"):
        setattr(message, name, getattr(decision, name))
    for name in ("outbound_path", "return_path"):
        setattr(message, name, [point_to_wire(point, point_factory) for point in getattr(decision, name)])
    for name in ("travel_time_s", "energy_est_wh", "min_clearance_m", "reserve_time_s", "reserve_wh"):
        value = getattr(decision, name)
        setattr(message, name, float("nan") if decision.status != "FEASIBLE" and value is None
                else float32(value, name))
    for name in ("oxygen_est_l", "reserve_oxygen_l"):
        setattr(message, name, float32(getattr(decision, name), name, oxygen_na=True))
    return message


def event_to_wire(event, message, stamp):
    set_header(message, event.run_id, stamp)
    for name in ("event_id", "seq", "causality_id", "event_type", "task_id", "agent_id",
                 "map_version", "route_id", "previous_state", "new_state", "reason_code", "detail"):
        value = getattr(event, name)
        setattr(message, name, 0 if name == "map_version" and value is None else value)
    return message


def snapshot_to_wire(snapshot, message, stamp, point_factory, route_factory, agent_messages):
    set_header(message, snapshot.run_id, stamp)
    for name in ("last_event_seq", "mission_state", "reason_code", "primary_agent_id",
                 "active_task_id", "active_task_kind", "active_task_state", "route_id"):
        setattr(message, name, getattr(snapshot, name))
    message.map_version = 0 if snapshot.map_version is None else snapshot.map_version
    message.base = point_to_wire(snapshot.base, point_factory)
    if snapshot.primary_goal is not None:
        message.primary_goal = point_to_wire(snapshot.primary_goal, point_factory)
    if snapshot.active_route is not None:
        message.active_route = decision_to_wire(snapshot.active_route, route_factory(), stamp, point_factory)
    # Preserve source orientation, velocity and source timestamps, which are not
    # observations retained by the deliberately smaller pure-Python core.
    message.agents = [agent_messages[agent.agent_id] for agent in snapshot.agents
                      if agent.agent_id in agent_messages]
    return message


def active_path_to_wire(route, message, stamp, pose_factory):
    message.header.frame_id = "map"
    message.header.stamp = stamp
    message.poses = []
    if route is not None:
        for point in route.outbound_path:
            pose = pose_factory()
            pose.header.frame_id = "map"
            pose.header.stamp = stamp
            for axis in "xyz":
                setattr(pose.pose.position, axis, finite_number(getattr(point, axis), axis))
            pose.pose.orientation.w = 1.0
            message.poses.append(pose)
    return message
