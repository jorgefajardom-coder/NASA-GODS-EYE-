"""Executable ICD boundary checks; a test harness, not a mission authority.

These helpers do not publish routes, update belief or calculate costs. Owners
must wire equivalent checks into their producers/consumers and record target ROS
evidence. No result from this harness establishes operational feasibility.
"""

from dataclasses import dataclass
from array import array
import hashlib
import json
import math
from collections.abc import Mapping

ROUTE_STATUSES = frozenset({"FEASIBLE", "UNKNOWN", "NO_PATH", "INSUFFICIENT_BUDGET", "STALE_MAP", "ERROR"})
ROUTE_MODES = frozenset({"FAST", "EFFICIENT", "SAFE"})
AGENT_KINDS = frozenset({"HUMAN", "ROVER", "DRONE"})
OXYGEN_FIELDS = frozenset({"oxygen_remaining_l", "oxygen_est_l", "oxygen_budget_l", "reserve_oxygen_l"})
DECISION_METRICS = frozenset({"travel_time_s", "energy_est_wh", "oxygen_est_l", "min_clearance_m",
                              "reserve_time_s", "reserve_wh", "reserve_oxygen_l"})


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _nonnegative(value):
    return _finite(value) and value >= 0


def ros_json(value, *, agent_kind=None, message_type=None):
    """Convert ROS-shaped trees using typed availability and NoData sentinels.

    Callers supply the owning agent kind for RouteDecision and service trees,
    which do not contain agent_kind. Generated TerrainMeta identifies its own
    NoData field; typed non-FEASIBLE RouteDecision permits unavailable metrics.
    ROS-shaped mappings require an explicit canonical type ID for these cases.
    ROS objects use their generated field list; arbitrary attributes are omitted.
    """
    if hasattr(value, "get_fields_and_field_types"):
        if type(value).__module__ == "mge_interfaces.msg._terrain_meta" and type(value).__name__ == "TerrainMeta":
            message_type = "mge_interfaces/msg/TerrainMeta"
        elif type(value).__module__ == "mge_interfaces.msg._route_decision" and type(value).__name__ == "RouteDecision":
            message_type = "mge_interfaces/msg/RouteDecision"
        value = {key: getattr(value, key) for key in value.get_fields_and_field_types()}
    if isinstance(value, Mapping):
        kind = value.get("agent_kind", agent_kind)
        if kind is not None and kind not in AGENT_KINDS:
            raise ValueError("UNKNOWN_AGENT_KIND")
        result = {}
        status = value.get("status")
        unavailable_decision = (message_type == "mge_interfaces/msg/RouteDecision"
                                and isinstance(status, str) and status in ROUTE_STATUSES
                                and status != "FEASIBLE")
        for key, item in value.items():
            if unavailable_decision and key in DECISION_METRICS and type(item) is float and math.isnan(item):
                result[key] = None
                continue
            if key == "nodata_value" and message_type == "mge_interfaces/msg/TerrainMeta":
                if type(item) is float and math.isnan(item):
                    result[key] = None
                    continue
            if key in OXYGEN_FIELDS:
                if kind not in AGENT_KINDS:
                    raise ValueError("OXYGEN_KIND_REQUIRED")
                if kind != "HUMAN":
                    if not (type(item) is float and math.isnan(item)):
                        raise ValueError("NONHUMAN_OXYGEN_MUST_BE_NAN")
                    result[key] = None
                    continue
                if not _nonnegative(item):
                    raise ValueError("HUMAN_OXYGEN_REQUIRED")
            result[key] = ros_json(item, agent_kind=kind)
        return result
    if isinstance(value, (tuple, list, array)):
        return [ros_json(item, agent_kind=agent_kind) for item in value]
    if type(value) is float and not math.isfinite(value):
        raise ValueError("NONFINITE_JSON_VALUE")
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise ValueError("UNSUPPORTED_JSON_TYPE")


def assert_public_payload(value):
    """Reject explicit hidden-reference/future-task fields anywhere in a tree.

    This is defense in depth for allowlisted artifacts, not a secrecy proof:
    producers also need filesystem/package audits, licensing and role review.
    """
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key).lower().replace("-", "_")
            if any(term in token for term in ("reference", "ground_truth", "groundtruth", "evaluator", "hidden", "future_tasks", "future_sites")):
                raise ValueError("EVALUATOR_REFERENCE_FORBIDDEN")
            if token in {"role", "layer_role"} and (not isinstance(item, str) or item not in {"prior", "belief", "sigma", "traversability", "public"}):
                raise ValueError("NONPUBLIC_ROLE")
            assert_public_payload(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            assert_public_payload(item)


@dataclass(frozen=True)
class GridGeometry:
    rows: int
    cols: int
    resolution_m: float
    origin_x_m: float = 0.0
    origin_y_m: float = 0.0

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in (self.rows, self.cols)):
            raise ValueError("INVALID_GRID_SHAPE")
        if not _nonnegative(self.resolution_m) or self.resolution_m == 0:
            raise ValueError("INVALID_RESOLUTION")
        if not all(_finite(v) for v in (self.origin_x_m, self.origin_y_m)):
            raise ValueError("INVALID_ORIGIN")

    def index(self, row, col):
        if any(type(v) is not int for v in (row, col)) or not (0 <= row < self.rows and 0 <= col < self.cols):
            raise ValueError("OUTSIDE_GRID")
        return row * self.cols + col

    def centre(self, row, col):
        self.index(row, col)
        return (self.origin_x_m + (col + .5) * self.resolution_m,
                self.origin_y_m + (row + .5) * self.resolution_m)

    def require_centre(self, point):
        if len(point) != 3 or not all(_finite(v) for v in point):
            raise ValueError("INVALID_POSITION")
        col = math.floor((point[0] - self.origin_x_m) / self.resolution_m)
        row = math.floor((point[1] - self.origin_y_m) / self.resolution_m)
        centre = self.centre(row, col)
        if any(abs(point[i] - centre[i]) > 1e-6 for i in (0, 1)):
            raise ValueError("NON_CELL_CENTER")
        return row, col


def enu_to_three(point):
    if len(point) != 3 or not all(_finite(v) for v in point):
        raise ValueError("INVALID_POSITION")
    return point[0], point[2], -point[1]


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class IdempotencyLedger:
    """Test-side request/event/observation identity checker, scoped to one run."""
    def __init__(self, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("RUN_REQUIRED")
        self.run_id = run_id
        self._seen = {}
        self._last_seq = -1

    def accept(self, namespace, identifier, payload, *, seq=None):
        if not isinstance(namespace, str) or namespace not in {"request", "event", "observation"} or not isinstance(identifier, str) or not identifier:
            raise ValueError("INVALID_IDENTITY")
        if payload.get("run_id") != self.run_id:
            raise ValueError("RUN_MISMATCH")
        digest = _digest(payload)
        key = namespace, identifier
        if key in self._seen:
            if self._seen[key] != (digest, seq):
                raise ValueError("IDEMPOTENCY_CONFLICT")
            return False
        if namespace == "event":
            if type(seq) is not int or not 0 <= seq < 2**64 or seq <= self._last_seq:
                raise ValueError("EVENT_SEQUENCE_REGRESSION")
            self._last_seq = seq
        elif seq is not None:
            raise ValueError("SEQUENCE_ONLY_FOR_EVENTS")
        self._seen[key] = digest, seq
        return True


class SnapshotLedger:
    """Check complete public batch envelopes without implementing map fusion.

    The envelope is a harness DTO, NOT an additional ROS or raster schema.
    Native ROS layers are associated by metadata's identical frame/stamp and
    explicit run/version context before calling this checker.
    """
    def __init__(self):
        self._stamps = {}
        self._versions = {}
        self._run = None
        self._retired = set()
        self._latest = -1

    def accept(self, batch):
        assert_public_payload(batch)
        if set(batch) != {"run_id", "dataset_id", "map_version", "frame_id", "stamp", "geometry", "layers"}:
            raise ValueError("UNEXPECTED_BATCH_FIELDS")
        run, version = batch["run_id"], batch["map_version"]
        if not isinstance(run, str) or not run or not batch["dataset_id"]:
            raise ValueError("BATCH_ID_REQUIRED")
        if type(version) is not int or not 0 <= version < 2**32 or batch["frame_id"] != "map":
            raise ValueError("INVALID_BATCH_IDENTITY")
        stamp = tuple(batch["stamp"])
        if (len(stamp) != 2 or any(type(v) is not int for v in stamp)
                or stamp[0] < 0 or not 0 <= stamp[1] < 10**9):
            raise ValueError("INVALID_STAMP")
        geometry = GridGeometry(**batch["geometry"])
        layers = batch["layers"]
        expected = {"belief", "sigma", "traversability/human", "traversability/rover", "traversability/drone"}
        if set(layers) != expected:
            raise ValueError("SNAPSHOT_INCOMPLETE_OR_UNEXPECTED")
        for name, layer in layers.items():
            if set(layer) != {"run_id", "map_version", "stamp", "frame_id", "values"}:
                raise ValueError("UNEXPECTED_LAYER_FIELDS")
            if (layer["run_id"], layer["map_version"], tuple(layer["stamp"]), layer["frame_id"]) != (run, version, stamp, "map"):
                raise ValueError("LAYER_IDENTITY_MISMATCH")
            values = layer["values"]
            if len(values) != geometry.rows * geometry.cols:
                raise ValueError("LAYER_SHAPE_MISMATCH")
            for item in values:
                if name.startswith("traversability/"):
                    if type(item) is not int or item not in (-1, 0, 100):
                        raise ValueError("INVALID_MASK")
                elif item is not None and (not _finite(item) or (name == "sigma" and item < 0)):
                    raise ValueError("INVALID_RASTER_VALUE")
        for index in range(geometry.rows * geometry.cols):
            if layers["belief"]["values"][index] is None or layers["sigma"]["values"][index] is None:
                if any(layers[f"traversability/{kind}"]["values"][index] == 0 for kind in ("human", "rover", "drone")):
                    raise ValueError("NODATA_MARKED_FREE")
        digest = _digest(batch)
        identity = run, version
        if run in self._retired:
            raise ValueError("RETIRED_RUN")
        if stamp in self._stamps and self._stamps[stamp] != identity:
            raise ValueError("STAMP_REUSED")
        if identity in self._versions:
            if self._versions[identity] != digest:
                raise ValueError("IMMUTABLE_BATCH_CHANGED")
            if run == self._run and version < self._latest:
                raise ValueError("STALE_MAP")
            return False
        if run == self._run and version < self._latest:
            raise ValueError("STALE_MAP")
        if self._run is not None and run != self._run:
            self._retired.add(self._run)
        self._run, self._latest = run, version
        self._stamps[stamp], self._versions[identity] = identity, digest
        return True


def candidate_rejection(request, decision, *, current_run, current_map_version,
                        model_agreed=False, recomputed_costs=None):
    """Return a reason without granting authority to execute any candidate.

    Inputs are already JSON-normalized canonical ROS fields. Resource sums are
    complete outbound + service + return. Independent science-model costs must
    be supplied; this helper does not substitute an estimator for either owner.
    """
    if not isinstance(request, Mapping) or not isinstance(decision, Mapping):
        return "INVALID_REQUEST_OR_DECISION"
    if (type(current_map_version) is not int or not 0 <= current_map_version < 2**32
            or type(request.get("map_version")) is not int or type(decision.get("map_version_used")) is not int):
        return "INVALID_MAP_VERSION"
    if not isinstance(current_run, str) or not current_run or request.get("run_id") != current_run or decision.get("run_id") != current_run:
        return "RUN_MISMATCH"
    if request.get("map_version") != current_map_version or decision.get("map_version_used") != current_map_version:
        return "STALE_MAP"
    if any(not request.get(key) or decision.get(key) != request[key] for key in ("request_id", "agent_id", "mode")):
        return "RESPONSE_MISMATCH"
    if (not isinstance(request["mode"], str) or request["mode"] not in ROUTE_MODES
            or not isinstance(request.get("agent_kind"), str) or request.get("agent_kind") not in AGENT_KINDS):
        return "INVALID_REQUEST_ENUM"
    status = decision.get("status")
    if not isinstance(status, str) or status not in ROUTE_STATUSES:
        return "INVALID_ROUTE_STATUS"
    if status != "FEASIBLE":
        return status
    if model_agreed is not True:
        return "MODEL_NOT_AGREED"
    if not isinstance(recomputed_costs, Mapping) or not recomputed_costs:
        return "MODEL_AUDIT_REQUIRED"
    if not isinstance(decision.get("route_id"), str) or not decision["route_id"] or not _nonnegative(decision.get("min_clearance_m")):
        return "INVALID_ROUTE"
    outbound, back = decision.get("outbound_path"), decision.get("return_path")
    def point(value):
        return isinstance(value, Mapping) and set(value) == {"x", "y", "z"} and all(_finite(v) for v in value.values())
    def near(a, b):
        return point(a) and point(b) and all(abs(a[k] - b[k]) <= 1e-6 for k in ("x", "y", "z"))
    if (not isinstance(outbound, list) or not outbound or not isinstance(back, list)
            or not all(point(p) for p in outbound + back)
            or not near(outbound[0], request.get("start")) or not near(outbound[-1], request.get("goal"))):
        return "INVALID_ROUTE_ENDPOINTS"
    if request.get("require_return") is not True or not back or not near(back[0], request["goal"]) or not near(back[-1], request.get("return_to")):
        return "RETURN_PATH_REQUIRED"
    if not _nonnegative(request.get("service_time_s")):
        return "INVALID_SERVICE_TIME"
    if not _nonnegative(decision.get("travel_time_s")) or decision["travel_time_s"] < request["service_time_s"]:
        return "INVALID_TOTAL_TIME"
    triples = [("travel_time_s", "time_budget_s", "reserve_time_s"),
               ("energy_est_wh", "energy_budget_wh", "reserve_wh")]
    if request["agent_kind"] == "HUMAN":
        triples.append(("oxygen_est_l", "oxygen_budget_l", "reserve_oxygen_l"))
    elif any(container.get(key) is not None for container, key in
             ((request, "oxygen_budget_l"), (request, "reserve_oxygen_l"),
              (decision, "oxygen_est_l"), (decision, "reserve_oxygen_l"))):
        return "OXYGEN_NOT_APPLICABLE"
    for cost_key, budget_key, reserve_key in triples:
        cost, budget, required, remaining = (decision.get(cost_key), request.get(budget_key),
                                             request.get(reserve_key), decision.get(reserve_key))
        audited = recomputed_costs.get(cost_key)
        if not all(_nonnegative(v) for v in (cost, budget, required, remaining, audited)):
            return "INVALID_RESOURCES"
        if not math.isclose(cost, audited, rel_tol=1e-5, abs_tol=1e-3):
            return "MODEL_MISMATCH"
        if cost + required > budget:
            return "INSUFFICIENT_BUDGET"
        if not math.isclose(remaining, budget - cost, rel_tol=1e-5, abs_tol=1e-3):
            return "RESERVE_MISMATCH"
    return ""


def logical_stop_on_map_change(route, *, current_run, current_map_version):
    """Describe a required logical stop; owner must apply/publish it in ROS."""
    stale = bool(route and (route.get("run_id") != current_run or route.get("map_version_used") != current_map_version))
    return {"invalidate_route": stale, "stop_required": stale,
            "reason_code": "STALE_MAP" if stale else ""}


def request_candidate(provider, request):
    """An injection seam shared by contractual mocks and owner-module adapters."""
    result = provider(request)
    if not isinstance(result, Mapping) or set(result) != {"decision"}:
        raise ValueError("PLAN_ROUTE_RESPONSE_REQUIRED")
    decision = result["decision"]
    if (not isinstance(decision, Mapping) or not isinstance(decision.get("status"), str) or decision.get("status") not in ROUTE_STATUSES
            or any(decision.get(key) != request.get(key) for key in ("run_id", "request_id", "agent_id", "mode"))):
        raise ValueError("INVALID_PLAN_ROUTE_RESPONSE")
    return dict(decision)
