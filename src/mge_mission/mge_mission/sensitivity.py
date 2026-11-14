"""Deterministic one-at-a-time model sensitivity, never execution evidence."""

from dataclasses import asdict, dataclass, replace
import math

from .models import AssumptionRecord, estimate_activity, estimate_segment
from .types import Budgets


@dataclass(frozen=True)
class SensitivityCase:
    case_id: str
    agent_id: str
    outbound_enu_m: tuple
    return_enu_m: tuple
    services: tuple = ()  # (activity, duration_s), each counted once
    wait_s: float = 0
    budgets: Budgets | None = None


def _budget(profile, budget):
    if budget is None:
        return
    for key, value in asdict(budget).items():
        if value is None and "oxygen" in key:
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("Budgets and reserves must be finite and nonnegative")
    if profile.kind == "human":
        if budget.oxygen_l is None or budget.reserve_oxygen_l is None:
            raise ValueError("Human oxygen budget and reserve are required")
    elif budget.oxygen_l is not None or budget.reserve_oxygen_l is not None:
        raise ValueError("Robots cannot have oxygen budgets")


def _evaluate(profile, case):
    _budget(profile, case.budgets)
    if (len(case.outbound_enu_m) < 2 or len(case.return_enu_m) < 2
            or tuple(case.outbound_enu_m[-1]) != tuple(case.return_enu_m[0])
            or tuple(case.outbound_enu_m[0]) != tuple(case.return_enu_m[-1])):
        raise ValueError("Supply explicit connected outbound and return paths to the same base")
    parts = {}
    for name, path in (("outbound", case.outbound_enu_m), ("return", case.return_enu_m)):
        parts[name] = [asdict(estimate_segment(profile, a, b)) for a, b in zip(path, path[1:])]
    parts["service"] = [asdict(estimate_activity(profile, activity, seconds))
                        for activity, seconds in case.services]
    parts["wait"] = [asdict(estimate_activity(profile, "idle", case.wait_s))]
    costs = [x for values in parts.values() for x in values]
    total = {key: sum(x[key] for x in costs) for key in ("time_s", "energy_wh")}
    total["oxygen_l"] = sum(x["oxygen_l"] for x in costs) if profile.kind == "human" else None
    margins = None
    if case.budgets is not None:
        b = case.budgets
        margins = {"time_s": b.time_s - b.reserve_time_s - total["time_s"],
                   "energy_wh": b.energy_wh - b.reserve_wh - total["energy_wh"]}
        if profile.kind == "human":
            margins["oxygen_l"] = b.oxygen_l - b.reserve_oxygen_l - total["oxygen_l"]
    return {"status": "ESTIMATED", "components": parts, "total": total,
            "reserve_margins": margins,
            "budget_feasible_under_model": all(x >= 0 for x in margins.values()) if margins else None}


def sweep(profiles, assumptions, cases):
    """Low/nominal/high per coefficient; preserve invalid variants as rejected rows.

    Full routes must be supplied. No terrain, task precedence or planning result is
    invented. Budget feasibility here is not authority to execute an optional task.
    """
    cases = tuple(cases)
    if not cases or len({x.case_id for x in cases}) != len(cases):
        raise ValueError("Supply nonempty uniquely identified sensitivity cases")
    records = [AssumptionRecord(**x) if isinstance(x, dict) else x for x in assumptions]
    if len({x.parameter for x in records}) != len(records):
        raise ValueError("Duplicate assumption paths")
    indexed = {}
    fixed = []
    for record in records:
        path = record.parameter.split(".")
        if len(path) == 2 and path[0] == "constants":
            fixed.append({**asdict(record), "sweep_status": "FIXED_MODEL_CONSTANT",
                          "reason": "Model constants are fixed; human oxygen_scale varies proportional O2 uncertainty."})
            continue
        if len(path) != 4 or path[0] != "profiles" or path[2] not in {"parameters", "activity_power_w"}:
            raise ValueError("Assumption must target a profile coefficient")
        _, agent, group, key = path
        if agent not in profiles or key not in getattr(profiles[agent], group):
            raise ValueError("Assumption targets an absent coefficient")
        if getattr(profiles[agent], group)[key] != record.value:
            raise ValueError("Registry coefficient and nominal assumption disagree")
        indexed.setdefault(agent, []).append((record, group, key))
    rows = []
    for case in cases:
        if not case.case_id or case.agent_id not in profiles:
            raise ValueError("Unknown case agent or empty case ID")
        profile = profiles[case.agent_id]
        # Malformed nominal inputs are input errors, not sensitivity outcomes.
        nominal = _evaluate(profile, case)
        if not indexed.get(case.agent_id):
            raise ValueError("Case agent has no traced sensitivity coefficients")
        for record, group, key in sorted(indexed[case.agent_id], key=lambda x: x[0].parameter):
            for level, value in (("low", record.sensitivity_min), ("nominal", record.value),
                                 ("high", record.sensitivity_max)):
                row = {"case_id": case.case_id, "agent_id": case.agent_id,
                       "parameter": record.parameter, "level": level, "value": value,
                       "unit": record.unit, "assumption_status": record.approval_status,
                       "profile_status": profile.approval_status, "source_url": record.source_url,
                       "source_locator": record.source_locator, "note": record.note,
                       "sensitivity_min": record.sensitivity_min, "nominal_value": record.value,
                       "sensitivity_max": record.sensitivity_max,
                       "origin": record.origin}
                try:
                    changed = dict(getattr(profile, group))
                    changed[key] = value
                    result = _evaluate(replace(profile, **{group: changed}), case)
                    result["delta_from_nominal"] = {
                        metric: result["total"][metric] - nominal["total"][metric]
                        if result["total"][metric] is not None else None for metric in nominal["total"]}
                    baseline = nominal["budget_feasible_under_model"]
                    result["budget_decision_changed"] = (
                        result["budget_feasible_under_model"] != baseline if baseline is not None else None)
                except ValueError as error:
                    result = {"status": "MODEL_REJECTED", "reason": str(error),
                              "budget_feasible_under_model": None,
                              "budget_decision_changed": None}
                rows.append({**row, **result})
    return {"schema_version": "1.0.0", "execution_kind": "MODEL_CHECK",
            "analysis_kind": "ONE_AT_A_TIME_SENSITIVITY", "scientific_approval": False,
            "fixed_assumptions": fixed,
            "integrated_mission_executed": False, "cases": [asdict(x) for x in cases],
            "limitations": ["Synthetic model estimates, not mission or A/B/C results.",
                            "One coefficient varies at a time; no joint uncertainty or confidence intervals.",
                            "No DEM soil inference, map clearance, task precedences or execution authority.",
                            "Reserves are separate; service and wait are counted once.",
                            "Parameters unused by these formula cases may show zero change."],
            "results": rows}
