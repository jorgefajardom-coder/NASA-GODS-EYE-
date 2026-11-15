"""Audit a verified, explicitly supplied planner snapshot on public synthetic cases.

This is model-conformance evidence, not a mission benchmark, scientific approval,
or permission to activate routes. The caller supplies trusted Python source;
hash verification identifies it and is not an execution sandbox.
"""

from contextlib import contextmanager
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
import types
import uuid

from . import models
from .models import CostEstimate, estimate_activity, estimate_segment, export_planner_profiles


RELATIVE_TOLERANCE = 1e-5
ABSOLUTE_TOLERANCE = 1e-3


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _profile_snapshot(profiles):
    return {key: {
        "agent_id": p.agent_id, "kind": p.kind, "capabilities": list(p.capabilities),
        "parameters": dict(p.parameters), "activity_power_w": dict(p.activity_power_w),
        "approval_status": p.approval_status, "model_id": p.model_id,
    } for key, p in sorted(profiles.items())}


def _verified_source(package_path, revision):
    """Require an explicit snapshot provenance manifest before executing source."""
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("planner_revision must be a full lowercase 40-character Git revision")
    supplied = Path(package_path).absolute()
    if any(part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction())
           for part in (supplied, *supplied.parents)):
        raise ValueError("planner package path must not traverse symlinks or junctions")
    package = supplied.resolve(strict=True)
    if not package.is_dir():
        raise ValueError("planner_package_path must name an explicit package directory")
    manifest_path = next((ancestor / "source_manifest.json" for ancestor in (package, *package.parents)
                          if (ancestor / "source_manifest.json").is_file()), None)
    if manifest_path is None:
        raise ValueError("trusted source_manifest.json is required; working checkouts are not inferred")
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest.get("schema_version") != "1.0.0" or manifest.get("revision") != revision:
        raise ValueError("planner source manifest version/revision does not match the requested snapshot")
    if manifest.get("repository") != "https://github.com/jorgefajardom-coder/NASA-GODS-EYE-.git":
        raise ValueError("unexpected planner source repository")
    root = manifest_path.parent.resolve()
    relative_package = _relative_path(manifest.get("package_root"))
    if (root / relative_package).resolve(strict=True) != package:
        raise ValueError("package path does not match the trusted manifest")
    hashes = manifest.get("files")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("source manifest must include content hashes")
    verified = {}
    for relative, expected in hashes.items():
        safe = _relative_path(relative)
        path = root / safe
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root):
            raise ValueError("source artifact escapes its snapshot")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("source manifest requires SHA-256 content hashes")
        actual = _digest(path.read_bytes())
        if actual != expected:
            raise ValueError(f"planner source hash mismatch: {relative}")
        verified[relative] = actual
    package_files = {path.relative_to(root).as_posix() for path in package.rglob("*.py")}
    required = {(package / name).relative_to(root).as_posix() for name in ("__init__.py", "core.py")}
    if not required <= package_files or not package_files <= hashes.keys():
        raise ValueError("every planner package Python file must be included in the source manifest")
    return package, {
        "revision": revision, "repository": manifest["repository"],
        "source_manifest_sha256": _digest(raw_manifest),
        "source_files_sha256": dict(sorted(verified.items())),
        "package_python_files": sorted(package_files),
    }


def _relative_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("manifest artifact paths must be relative POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ":" in value:
        raise ValueError("manifest artifact path escapes its snapshot")
    return Path(*path.parts)


def _load_dependencies():
    numpy = importlib.import_module("numpy")
    scipy = importlib.import_module("scipy")
    importlib.import_module("scipy.spatial")
    return numpy, {"numpy": numpy.__version__, "scipy": scipy.__version__}


@contextmanager
def _isolated_core(package, *, scientific=False):
    """Register only private module aliases; leave public sys.path untouched.

    The package initializer is hashed but not executed. Core source is compiled
    directly to avoid writing bytecode into the supplied read-only snapshot.
    """
    alias = "_mge_conformance_" + uuid.uuid4().hex
    package_module = types.ModuleType(alias)
    package_module.__package__ = alias
    package_module.__path__ = [str(package)]
    package_module.__spec__ = importlib.util.spec_from_file_location(
        alias, package / "__init__.py", submodule_search_locations=[str(package)])
    name = alias + ".core"
    spec = importlib.util.spec_from_file_location(name, package / "core.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = package_module
    sys.modules[name] = module
    try:
        exec(compile((package / "core.py").read_bytes(), str(package / "core.py"), "exec"), module.__dict__)
        if scientific:
            backend_name = alias + ".resource_costs"
            backend_path = package / "resource_costs.py"
            backend_spec = importlib.util.spec_from_file_location(backend_name, backend_path)
            backend = importlib.util.module_from_spec(backend_spec)
            sys.modules[backend_name] = backend
            exec(compile(backend_path.read_bytes(), str(backend_path), "exec"), backend.__dict__)
            module.scientific_backend = backend
        yield module
    finally:
        for key in tuple(sys.modules):
            if key == alias or key.startswith(alias + "."):
                del sys.modules[key]


def _field(value, name):
    try:
        return value[name] if isinstance(value, dict) else getattr(value, name)
    except (KeyError, AttributeError) as exc:
        raise ValueError(f"planner result lacks {name}") from exc


def _resource(value, *, nullable=False):
    if nullable and (value is None or isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("planner cost must be finite; only nonhuman oxygen may be unavailable")
    return float(value)


def _sum_costs(profile, costs):
    values = list(costs)
    return CostEstimate(sum(c.time_s for c in values), sum(c.energy_wh for c in values),
                        sum(c.oxygen_l for c in values) if profile.kind == "human" else None)


def audit_returned_paths(profile, decision, *, service_activity, service_time_s,
                         wait_time_s=0.0, budget=None,
                         relative_tolerance=RELATIVE_TOLERANCE,
                         absolute_tolerance=ABSOLUTE_TOLERANCE):
    """Recompute the actual returned directed paths, service, and waiting once."""
    for tolerance in (relative_tolerance, absolute_tolerance):
        if isinstance(tolerance, bool) or not isinstance(tolerance, (float, int)) or not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError("comparison tolerances must be finite and nonnegative")
    pieces = []
    paths = {}
    for name in ("outbound_path", "return_path"):
        path = tuple(tuple(point) for point in _field(decision, name))
        if not path:
            raise ValueError("FEASIBLE round-trip result must contain both returned paths")
        # Even one-point paths must contain valid ENU values.
        estimate_segment(profile, path[0], path[0])
        pieces.extend(estimate_segment(profile, a, b) for a, b in zip(path, path[1:]))
        paths[name] = [list(point) for point in path]
    if paths["outbound_path"][-1] != paths["return_path"][0]:
        raise ValueError("returned paths do not connect at the service goal")
    pieces.append(estimate_activity(profile, service_activity, service_time_s))
    pieces.append(estimate_activity(profile, "wait", wait_time_s))
    science = _sum_costs(profile, pieces)
    actual = {"time_s": science.time_s, "energy_wh": science.energy_wh, "oxygen_l": science.oxygen_l}
    reported = {key: _resource(_field(decision, field), nullable=key == "oxygen_l" and profile.kind != "human")
                for key, field in (("time_s", "travel_time_s"), ("energy_wh", "energy_est_wh"), ("oxygen_l", "oxygen_est_l"))}
    if profile.kind != "human" and reported["oxygen_l"] is not None:
        raise ValueError("nonhuman planner result must not contain human oxygen")
    reported_reserves = {key: _resource(_field(decision, field), nullable=key == "oxygen_l" and profile.kind != "human")
                         for key, field in (("time_s", "reserve_time_s"), ("energy_wh", "reserve_wh"), ("oxygen_l", "reserve_oxygen_l"))}
    if profile.kind != "human" and reported_reserves["oxygen_l"] is not None:
        raise ValueError("nonhuman planner reserve must not contain human oxygen")
    science_reserves = None if budget is None else {
        key: None if key == "oxygen_l" and profile.kind != "human" else _resource(budget[key]) - actual[key]
        for key in actual}
    def compare(left, right):
        return {key: left[key] is None and right[key] is None if left[key] is None or right[key] is None
                else math.isclose(left[key], right[key], rel_tol=relative_tolerance, abs_tol=absolute_tolerance)
                for key in left}
    costs_match = compare(reported, actual)
    reserves_match = None if science_reserves is None else compare(reported_reserves, science_reserves)
    deltas = {key: None if actual[key] is None or reported[key] is None else reported[key] - actual[key] for key in actual}
    reserve_deltas = None if science_reserves is None else {
        key: None if science_reserves[key] is None or reported_reserves[key] is None else reported_reserves[key] - science_reserves[key]
        for key in actual}
    return {"paths": paths, "planner_costs": reported, "science_costs": actual,
            "planner_reserves": reported_reserves, "science_reserves": science_reserves,
            "cost_deltas_planner_minus_science": deltas,
            "reserve_deltas_planner_minus_science": reserve_deltas,
            "costs_within_tolerance": costs_match, "reserves_within_tolerance": reserves_match,
            "agreement": all(costs_match.values()) and (reserves_match is None or all(reserves_match.values()))}


def _cases(profiles):
    selected = {kind: next((p for _, p in sorted(profiles.items()) if p.kind == kind), None)
                for kind in ("human", "rover", "drone")}
    if any(profile is None for profile in selected.values()):
        raise ValueError("conformance requires human, rover, and drone profiles")
    return [("human_flat", selected["human"], 0.0, "sample", 0.0, 0.0),
            ("human_slope", selected["human"], 0.05, "sample", 0.0, 0.0),
            ("human_service_wait", selected["human"], 0.0, "sample", 20.0, 15.0),
            ("rover_flat", selected["rover"], 0.0, "inspect", 0.0, 0.0),
            ("rover_slope", selected["rover"], 0.05, "inspect", 0.0, 0.0),
            ("rover_service_wait", selected["rover"], 0.0, "inspect", 20.0, 15.0),
            ("drone_observe", selected["drone"], 0.0, "observe", 30.0, 0.0)]


def run_conformance(planner_package_path, profiles, planner_revision, *, backend="scientific"):
    """Run seven actual planner calls; always leave route authorization BLOCKED."""
    if backend not in {"scientific", "legacy"}:
        raise ValueError("backend must be scientific or explicitly selected legacy")
    package, provenance = _verified_source(planner_package_path, planner_revision)
    profile_snapshot = _profile_snapshot(profiles)
    report = {
        "schema_version": "1.0.0", "classification": "MODEL_CONFORMANCE",
        "synthetic": True, "authorization": "BLOCKED", "scientific_approval_changed": False,
        "status": "NOT_RUN", "reason_code": "NOT_STARTED", "planner": provenance,
        "cost_backend": backend,
        "science": {"model_id": models.MODEL_ID,
                    "model_source_sha256": _digest(Path(models.__file__).read_bytes()),
                    "probe_source_sha256": _digest(Path(__file__).read_bytes()),
                    "profiles_sha256": _digest(_canonical(profile_snapshot)),
                    "profiles": profile_snapshot,
                    "oxygen_volume_basis": {"gas": "ideal dry O2", "temperature_k": 273.15, "pressure_pa": 101325}},
        "tolerances": {"relative": RELATIVE_TOLERANCE, "absolute": ABSOLUTE_TOLERANCE},
        "cases": [],
        "limits": ["Synthetic known-public grids, not mission execution or an A/B/C benchmark.",
                   "Agreement on finite cases cannot approve profiles or planner model identity.",
                   "No evaluator reference, hidden observations, or LIVE mission is used."]}
    cases = _cases(profiles)
    try:
        numpy, versions = _load_dependencies()
    except (ImportError, OSError) as exc:
        report.update(reason_code="DEPENDENCIES_UNAVAILABLE", dependency_error=f"{type(exc).__name__}: {exc}")
        return report
    report["dependencies"] = versions
    projection = export_planner_profiles(profiles)
    report["planner_projection"] = projection
    report["planner_projection_cost_rates_applied"] = backend == "legacy"
    try:
        with _isolated_core(package, scientific=backend == "scientific") as core:
            for case_id, profile, grade, activity, service, wait in cases:
                case = {"case_id": case_id, "agent_id": profile.agent_id, "status": "ERROR"}
                report["cases"].append(case)
                try:
                    terrain = numpy.tile(numpy.arange(13, dtype=float) * grade, (13, 1))
                    start = (4.5, 4.5, float(terrain[4, 4]))
                    goal = (6.5, 4.5, float(terrain[4, 6]))
                    budget = {"time_s": 100000.0, "energy_wh": 100000.0,
                              "oxygen_l": 100000.0 if profile.kind == "human" else None}
                    inputs = {"grid_rows": 13, "grid_cols": 13, "resolution_m": 1.0,
                              "height_per_column_m": grade, "all_cells_public_admissible": True,
                              "sigma_m": 0.0, "start_enu_m": start, "goal_enu_m": goal,
                              "return_to_enu_m": start, "service_activity": activity,
                              "service_time_s": service, "wait_time_s": wait,
                              "budget": budget, "required_reserve_time_s": 10.0,
                              "required_reserve_wh": 10.0,
                              "required_reserve_oxygen_l": 10.0 if profile.kind == "human" else None}
                    case["inputs"] = inputs
                    case["inputs_sha256"] = _digest(_canonical(inputs))
                    grid = core.TerrainGrid(run_id="conformance-" + case_id, map_version=1,
                                            elevation_m=terrain, traversability=numpy.zeros((13, 13), dtype=int),
                                            resolution_m=1.0, sigma_m=numpy.zeros((13, 13)))
                    motion = core.MotionProfile(**projection["profiles"][profile.agent_id])
                    resources = core.ResourceBudget(agent_kind=profile.kind, time_s=budget["time_s"],
                                                    energy_wh=budget["energy_wh"], reserve_wh=10.0,
                                                    oxygen_l=budget["oxygen_l"],
                                                    reserve_oxygen_l=10.0 if profile.kind == "human" else None)
                    request = core.PlanRequest(run_id=grid.run_id, request_id=case_id,
                                               agent_id=profile.agent_id, agent_kind=profile.kind, map_version=1,
                                               start=start, goal=goal, return_to=start, require_return=True,
                                               mode="FAST", budget=resources, service_time_s=service + wait,
                                               reserve_time_s=10.0)
                    if backend == "scientific":
                        shared = core.scientific_backend
                        activities = (shared.Activity(case_id + ":service", activity, service),
                                      shared.Activity(case_id + ":wait", "wait", wait))
                        decision = shared.scientific_plan_route(
                            terrain=grid, request=request, motion_profile=motion,
                            scientific_profile=profile, activities=activities)
                    else:
                        decision = core.plan_route(terrain=grid, request=request, profile=motion)
                    status = _field(decision, "status")
                    case["planner_status"] = getattr(status, "value", status)
                    case["planner_reason_code"] = _field(decision, "reason_code")
                    if case["planner_status"] != "FEASIBLE":
                        case["status"] = "NOT_FEASIBLE"
                        continue
                    outbound = _field(decision, "outbound_path")
                    inbound = _field(decision, "return_path")
                    if not outbound or not inbound:
                        raise ValueError("candidate omits a requested round-trip path")
                    endpoints = ((outbound[0], start), (outbound[-1], goal),
                                 (inbound[0], goal), (inbound[-1], start))
                    if any(len(actual) != 3 or any(not math.isclose(a, b, rel_tol=0, abs_tol=1e-6)
                                                  for a, b in zip(actual, expected))
                           for actual, expected in endpoints):
                        raise ValueError("candidate paths do not match the requested synthetic endpoints")
                    audit = audit_returned_paths(profile, decision, service_activity=activity,
                                                 service_time_s=service, wait_time_s=wait, budget=budget)
                    case["audit"] = audit
                    case["status"] = "AGREE" if audit["agreement"] else "DISAGREE"
                except Exception as exc:
                    case["error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        report.update(status="ERROR", reason_code="PLANNER_IMPORT_ERROR", error=f"{type(exc).__name__}: {exc}")
        return report
    _verified_source(package, planner_revision)
    counts = {status: sum(case["status"] == status for case in report["cases"])
              for status in ("AGREE", "DISAGREE", "NOT_FEASIBLE", "ERROR")}
    report.update(status="COMPLETED", reason_code="MODEL_DISAGREEMENT" if counts["DISAGREE"] else
                  "CASES_NOT_AUDITED" if counts["ERROR"] or counts["NOT_FEASIBLE"] else "ALL_CASES_AGREE",
                  summary=counts)
    return report
