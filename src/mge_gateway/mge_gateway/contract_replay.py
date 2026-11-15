"""Additive, offline reconciliation of the 1.0.0 recorder and legacy viewer.

This module does not replace either implementation or authorize mission routes.
All input paths are local. Public rasters are an explicit attachment: the
recorder writes it as public_rasters.json when the run published the observed
mask (read_public_rasters), and older packages simply lack it.
"""
from copy import deepcopy
import json
import math
from pathlib import Path

from mge_gateway.store import DECLARABLE_SOURCE_MODES, mock_evidence

SCHEMA = "1.0.0"
VIEWER_SCHEMA = "mge-web-0.1-draft"
PUBLIC_RASTER_SCHEMA = "mge-public-rasters-1.0.0"
KINDS = {"state", "event", "terrain_meta"}
FILES = {"timeline": "timeline.jsonl", "snapshot": "snapshot.json"}
RASTER_FILE = "public_rasters.json"
ROUTE_STATES = {"FEASIBLE", "UNKNOWN", "NO_PATH", "INSUFFICIENT_BUDGET", "STALE_MAP", "ERROR"}
GEOMETRY = ("dataset_id", "rows", "cols", "origin_x_m", "origin_y_m",
            "resolution_m", "crs", "origin_lat_deg", "origin_lon_deg", "vertical_datum")


class ReplayContractError(ValueError):
    """Malformed or unsupported input; never manufacture replacement data."""


def _need(condition, reason):
    if not condition:
        raise ReplayContractError(reason)


def _no_constants(token):
    raise ReplayContractError(f"Non-standard JSON token: {token}")


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_constant=_no_constants)
    except (OSError, ValueError) as exc:
        raise ReplayContractError(f"{path.name}: {exc}") from exc


def _public(value):
    """Reject evaluator content recursively, including in nested attachments."""
    if isinstance(value, dict):
        for key, child in value.items():
            _need(key.lower() not in {"reference", "reference_dem", "ground_truth", "evaluator_reference"},
                  "EVALUATOR_REFERENCE_FORBIDDEN")
            _public(child)
    elif isinstance(value, list):
        for child in value:
            _public(child)
    elif isinstance(value, float):
        _need(math.isfinite(value), "NON_JSON_NUMBER")


def _envelope(obj, run):
    _need(isinstance(obj, dict), "ENVELOPE_OBJECT_REQUIRED")
    _need(obj.get("schema_version") == SCHEMA, "UNSUPPORTED_SCHEMA")
    _need(obj.get("run_id") == run and bool(run), "RUN_MISMATCH")
    _need(obj.get("mode") == "REPLAY", "REPLAY_MODE_REQUIRED")
    _need(_finite(obj.get("timestamp_sim_s")), "INVALID_CLOCK")
    _need(_integer(obj.get("map_version"))
          and obj["map_version"] >= 0, "INVALID_MAP_VERSION")


def validate_package(manifest, records, snapshot):
    """Validate recorded snapshots and timeline without importing ROS.

    Saved duplicate events are rejected; deduplication belongs at ingestion.
    State snapshots may precede their corresponding events in arrival order.
    Late events retain arrival order; the snapshot history is ordered by seq.
    This check validates serialization/identity, not scientific feasibility.
    """
    run = manifest.get("run_id")
    _public([manifest, records, snapshot])
    _envelope(manifest, run)
    _envelope(snapshot, run)
    # public_rasters is optional: packages without the observed mask lack it.
    _need(manifest.get("files") in (FILES, {**FILES, "public_rasters": RASTER_FILE}),
          "UNSUPPORTED_FILE_LAYOUT")
    _need(manifest.get("record_count") == len(records), "RECORD_COUNT_MISMATCH")
    # Optional: absent in packages recorded before the field existed. A
    # recording cannot vouch for a validated live mission.
    _need(manifest.get("source_mode", "UNKNOWN") in DECLARABLE_SOURCE_MODES, "INVALID_SOURCE_MODE")
    events, state, meta = [], None, None
    seen_ids, seen_seqs = set(), set()
    last_time, state_seq, state_map, envelope_map = -math.inf, -1, -1, -1
    geometry = None
    routes = {}
    for rec in records:
        _envelope(rec, run)
        _need(rec["timestamp_sim_s"] >= last_time, "CLOCK_REGRESSION")
        _need(rec["map_version"] >= envelope_map, "ENVELOPE_MAP_REGRESSION")
        last_time, envelope_map = rec["timestamp_sim_s"], rec["map_version"]
        kind = rec.get("type")
        _need(kind in KINDS and isinstance(rec.get(kind), dict), "INVALID_RECORD_TYPE")
        body = rec[kind]
        _need(body.get("run_id") == run, "PAYLOAD_RUN_MISMATCH")
        if kind == "terrain_meta":
            _need(body.get("header", {}).get("frame_id") == "map", "INVALID_FRAME")
            _need(body.get("map_version") == rec["map_version"], "META_MAP_MISMATCH")
            current = tuple(body.get(k) for k in GEOMETRY)
            _need(geometry is None or current == geometry, "GEOMETRY_CHANGE_REQUIRES_NEW_DATASET")
            geometry, meta = current, body
        elif kind == "event":
            eid, seq = body.get("event_id"), body.get("seq")
            _need(bool(eid) and eid not in seen_ids, "DUPLICATE_EVENT_ID")
            _need(_integer(seq) and 0 < seq < 2**64, "INVALID_EVENT_SEQ")
            _need(seq not in seen_seqs, "DUPLICATE_EVENT_SEQ")
            seen_ids.add(eid)
            seen_seqs.add(seq)
            events.append(body)
        else:
            seq, version = body.get("last_event_seq"), body.get("map_version")
            _need(_integer(seq) and seq >= 0 and seq >= state_seq, "STATE_SEQ_REGRESSION")
            _need(_integer(version) and version >= 0 and version >= state_map, "STATE_MAP_REGRESSION")
            # Topics arrive in any order, so a state may lag the newest map the
            # package recorded (version 0 before the mission has a map). It
            # never runs ahead of it, and its route must match its own version.
            _need(version <= rec["map_version"], "STATE_AHEAD_OF_MAP")
            state_seq, state_map, state = seq, version, body
            _need(body.get("header", {}).get("frame_id") == "map", "INVALID_FRAME")
            for agent in body.get("agents", []):
                _need(agent.get("run_id") == run, "AGENT_RUN_MISMATCH")
                _need(agent.get("agent_kind") in {"HUMAN", "ROVER", "DRONE"}, "INVALID_AGENT_KIND")
                if agent["agent_kind"] != "HUMAN":
                    _need(agent.get("oxygen_remaining_l") is None, "NON_HUMAN_OXYGEN_MUST_BE_NULL")
            route_id = body.get("route_id", "")
            route = body.get("active_route")
            if route_id:
                _need(isinstance(route, dict) and route.get("run_id") == run, "ROUTE_RUN_MISMATCH")
                _need(route.get("route_id") == route_id, "ROUTE_ID_MISMATCH")
                _need(route.get("map_version_used") == version, "STALE_ROUTE")
                _need(route.get("status") in ROUTE_STATES, "INVALID_ROUTE_STATUS")
                _need(route.get("status") == "FEASIBLE", "ACTIVE_ROUTE_NOT_FEASIBLE")
                previous = routes.get(route_id)
                # Header timestamps can refresh; route identity/content cannot.
                normalized = {k: v for k, v in route.items() if k != "header"}
                _need(previous is None or previous == normalized, "ROUTE_ID_REUSED")
                routes[route_id] = normalized
    _need(snapshot.get("mission_state") == state, "SNAPSHOT_STATE_MISMATCH")
    _need(snapshot.get("events") == sorted(events, key=lambda event: event["seq"]),
          "SNAPSHOT_EVENTS_MISMATCH")
    _need(snapshot.get("terrain_meta") == meta and manifest.get("terrain_meta") == meta,
          "SNAPSHOT_META_MISMATCH")
    _need(manifest.get("event_count") == len(events), "EVENT_COUNT_MISMATCH")
    _need(manifest["map_version"] == snapshot["map_version"] == envelope_map, "FINAL_MAP_MISMATCH")
    _need(manifest["timestamp_sim_s"] == snapshot["timestamp_sim_s"] == last_time, "FINAL_CLOCK_MISMATCH")


def read_package(directory):
    """Read only the three fixed filenames; manifest paths cannot escape."""
    root = Path(directory)
    manifest = _read(root / "manifest.json")
    snapshot = _read(root / "snapshot.json")
    try:
        records = [json.loads(line, parse_constant=_no_constants)
                   for line in (root / "timeline.jsonl").read_text(encoding="utf-8").splitlines()
                   if line.strip()]
    except (OSError, ValueError) as exc:
        raise ReplayContractError(f"timeline.jsonl: {exc}") from exc
    validate_package(manifest, records, snapshot)
    return manifest, records, snapshot


def read_public_rasters(directory, manifest):
    """The recorded attachment named by the manifest, or None if it has none."""
    name = manifest.get("files", {}).get("public_rasters")
    if name is None:
        return None
    _need(name == RASTER_FILE, "UNSUPPORTED_FILE_LAYOUT")
    attachment = _read(Path(directory) / RASTER_FILE)
    _public(attachment)
    return attachment


def write_package(directory, manifest, records, snapshot):
    """Encode a validated offline fixture; never overwrite an existing run.

    The ROS recorder remains the owner of live recording. This encoder enables
    deterministic offline contract round trips and takes already recorded data.
    """
    validate_package(manifest, records, snapshot)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    (root / "manifest.json").write_text(json.dumps(manifest, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    (root / "snapshot.json").write_text(json.dumps(snapshot, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    (root / "timeline.jsonl").write_text("".join(json.dumps(r, allow_nan=False) + "\n" for r in records), encoding="utf-8")


def _flatten(body, origin, fallback):
    out = deepcopy(body)
    header = out.pop("header", None)
    if header:
        stamp = header["stamp"]
        out["timestamp_source_s"] = stamp["sec"] + stamp["nanosec"] / 1e9
        out["timestamp_sim_s"] = out["timestamp_source_s"] - origin
    else:
        out["timestamp_sim_s"] = fallback
    return out


def _rasters(attachment, manifest, versions, recorded):
    """versions: map versions the mission used; recorded: terrain versions seen.

    Version 0 means no map has been received, so it needs no raster. Every
    other used version must be present (no nearest-version fallback), and the
    attachment may only add versions whose metadata the package recorded.
    """
    _public(attachment)
    meta = manifest["terrain_meta"]
    _need(isinstance(attachment, dict), "RASTER_OBJECT_REQUIRED")
    _need(attachment.get("schema_version") == PUBLIC_RASTER_SCHEMA, "UNSUPPORTED_RASTER_SCHEMA")
    for key in ("run_id", "dataset_id", "rows", "cols"):
        _need(attachment.get(key) == (manifest["run_id"] if key == "run_id" else meta[key]),
              "RASTER_IDENTITY_MISMATCH")
    _need(attachment.get("terrain_geometry") == {k: meta[k] for k in GEOMETRY}, "RASTER_GEOMETRY_MISMATCH")
    _need(_integer(meta["rows"]) and _integer(meta["cols"]), "INVALID_RASTER_DIMENSIONS")
    count = meta["rows"] * meta["cols"]
    _need(count > 0, "INVALID_RASTER_DIMENSIONS")
    def grid(values, sigma=False):
        _need(isinstance(values, list) and len(values) == count, "RASTER_LENGTH_MISMATCH")
        _need(all(v is None or (_finite(v) and (not sigma or v >= 0)) for v in values),
              "INVALID_RASTER_VALUE")
    grid(attachment.get("prior"))
    layers = attachment.get("versions", {})
    _need(isinstance(layers, dict)
          and {str(v) for v in versions if v != 0} <= set(layers) <= {str(v) for v in recorded},
          "RASTER_VERSION_MISMATCH")
    for layer in layers.values():
        grid(layer.get("belief"))
        grid(layer.get("sigma"), True)
        observed = layer.get("observed")
        _need(isinstance(observed, list) and all(isinstance(i, int) and not isinstance(i, bool)
              and 0 <= i < count for i in observed), "INVALID_OBSERVED_INDEX")
        _need(len(set(observed)) == len(observed), "DUPLICATE_OBSERVED_INDEX")
        if "impassable" in layer:   # optional addition to 1.0.0
            blocked = layer["impassable"]
            _need(isinstance(blocked, list) and all(isinstance(i, int) and not isinstance(i, bool)
                  and 0 <= i < count for i in blocked), "INVALID_IMPASSABLE_INDEX")
            _need(len(set(blocked)) == len(blocked), "DUPLICATE_IMPASSABLE_INDEX")
    return {"run_id": manifest["run_id"], "rows": meta["rows"], "cols": meta["cols"],
            "prior": deepcopy(attachment["prior"]), "versions": deepcopy(layers),
            # Legacy shape only: every cell is explicitly NoData. No reference
            # is accepted as input or serialized, including in evaluator mode.
            "reference": [None] * count}


def check_public_rasters(manifest, records, attachment):
    """Validate a raster attachment against a package's recorded versions."""
    versions = {r["state"]["map_version"] for r in records if r.get("type") == "state"}
    recorded = {r["terrain_meta"]["map_version"] for r in records if r.get("type") == "terrain_meta"}
    _need(manifest.get("terrain_meta") is not None, "NO_TERRAIN_META")
    _rasters(attachment, manifest, versions, recorded)


def to_viewer(manifest, records, snapshot, public_rasters=None):
    """Convert to Jorge's four-file shape; fail closed without public rasters.

    Returned timeline/routes are useful even when raster attachment is absent,
    but files are not loadable as a terrain replay until status is READY.
    """
    validate_package(manifest, records, snapshot)
    origin = manifest.get("time_start_sim_s")
    _need(_finite(origin), "INVALID_START_TIME")
    run, meta = manifest["run_id"], manifest["terrain_meta"]
    _need(meta is not None, "NO_TERRAIN_META")
    frames, events, routes, versions, recorded = [], [], {}, set(), set()
    for rec in records:
        kind, t = rec["type"], rec["timestamp_sim_s"] - origin
        body = rec[kind]
        if kind == "terrain_meta":
            recorded.add(body["map_version"])
        if kind == "event":
            event = _flatten(body, origin, t)
            event["timestamp_sim_s"] = t  # recorded arrival, not earlier source stamp
            events.append(event)
        elif kind == "state":
            state = _flatten(body, origin, t)
            state["timestamp_sim_s"] = t
            state["agents"] = [_flatten(a, origin, t) for a in state.get("agents", [])]
            if state.get("route_id"):
                route = _flatten(body["active_route"], origin, t)
                state["active_route"] = route
                routes.setdefault(route["route_id"], route)
            else:
                state.pop("active_route", None)
            versions.add(state["map_version"])
            frames.append({"timestamp_sim_s": t, "mission_state": state})
    # Packages recorded before source_mode existed only have terrain evidence.
    declared = manifest.get("source_mode", "UNKNOWN")
    source_mode = "MOCK" if mock_evidence(meta) else declared
    source_mock = source_mode == "MOCK"
    viewer_meta = deepcopy(meta)
    viewer_meta["frame_id"] = viewer_meta.pop("header")["frame_id"]
    viewer_manifest = {
        "schema_version": VIEWER_SCHEMA, "icd": "ICD-ROS2-V1",
        "run_id": run, "mode": "REPLAY", "source_mode": source_mode,
        "clock_source": manifest.get("clock_source", "unknown"),
        "recorded_from": manifest.get("recorded_from"),
        "provenance": ["replay", *(["simulated"] if source_mode in ("MOCK", "SIMULATION") else [])],
        "illustrative": source_mock, "title": f"REPLAY{'' if source_mode == 'UNKNOWN' else ' / ' + source_mode}: {run}",
        "summary": "Converted recorded state; no route or scientific calculations performed.",
        "disclaimer": "Recorded replay. Source clock: " + str(manifest.get("clock_source", "unknown"))
                      + ". Scientific and operational acceptance pending.",
        "duration_s": manifest["timestamp_sim_s"] - origin,
        "terrain_meta": viewer_meta, "vertical_exaggeration_default": 1,
        "control_points": [], "pois": [], "reference_available": False,
        "files": {"rasters": "rasters.json", "timeline": "timeline.json", "routes": "routes.json"},
    }
    return {
        "status": "READY" if public_rasters is not None else "NOT_READY",
        "reason_code": "" if public_rasters is not None else "PUBLIC_RASTERS_REQUIRED",
        "manifest": viewer_manifest,
        "timeline": {"schema_version": VIEWER_SCHEMA, "run_id": run, "frames": frames, "events": events},
        "routes": {"run_id": run, "routes": list(routes.values())},
        "rasters": (_rasters(public_rasters, manifest, versions, recorded)
                    if public_rasters is not None else None),
    }
