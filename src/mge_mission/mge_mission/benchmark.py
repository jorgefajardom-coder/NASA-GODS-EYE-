"""Summarize externally supplied A/B/C outcomes without running a mission.

The report checks declared protocol consistency. Filesystem evidence validation
is supplied by the separate audit boundary; neither operation approves science.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import math
import re


PREDICATES = (
    "primary_goal_completed", "returned_to_base_within_tolerance",
    "verified_ground_traversal_under_model", "no_budget_violation",
)
METRICS = (
    "verified_ground_fraction", "unsafe_step_count", "optional_tasks_accepted",
    "optional_tasks_rejected", "time_to_verified_route_s", "mission_duration_s",
    "energy_est_wh", "oxygen_est_l", "replan_count", "replan_latency_ms", "max_map_age_s",
)
COUNT_METRICS = {"unsafe_step_count", "optional_tasks_accepted", "optional_tasks_rejected", "replan_count"}
CONTEXT_FIELDS = {
    "scenario_id", "mission_config_sha256", "dataset_manifest_sha256", "prior_sha256",
    "initial_belief_sha256", "profile_registry_sha256", "model_id", "model_source_sha256",
    "observation_model_sha256", "task_generator_sha256", "reference_id", "profile_status",
}
TERMINATION_STATES = {"IDLE", "PLANNING", "READY", "ACTIVE", "REPLAN", "RETURNING",
                      "COMPLETE", "BLOCKED", "ABORTED"}


def _canonical(value):
    def check(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                check(child)
            return
        raise ValueError("records require finite JSON values and string object keys")
    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=False)


def _text(value):
    return type(value) is str and bool(value.strip())


def _hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _revision(value):
    return type(value) is str and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value) is not None


def _utc(value):
    if type(value) is not str:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result if result.tzinfo is not None and result.utcoffset() == timedelta(0) else None


def _finding(code, detail):
    return {"severity": "error", "code": code, "detail": detail}


@dataclass(frozen=True)
class FrozenBenchmarkPlan:
    _json: str

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict:
            raise ValueError("benchmark plan must be a JSON object")
        data = json.loads(_canonical(value))
        claimed = data.pop("freeze_sha256", None)
        if data.get("schema_version") != "1.0.0" or data.get("status") != "frozen":
            raise ValueError("only an explicitly frozen schema 1.0.0 plan can be executed")
        if not _text(data.get("benchmark_id")) or _utc(data.get("frozen_at_utc")) is None:
            raise ValueError("benchmark ID and UTC freeze timestamp required")
        if data.get("policies") != ["A", "B", "C"]:
            raise ValueError("the declared policies must be A, B and C in that order")
        seeds = data.get("planned_seeds")
        if (type(seeds) is not list or not seeds or any(type(x) is not int or x < 0 for x in seeds)
                or len(set(seeds)) != len(seeds)):
            raise ValueError("planned seeds must be explicit, unique nonnegative integers")
        if data.get("experiment_kind") not in ("nominal", "sensitivity"):
            raise ValueError("experiment kind must be nominal or sensitivity")
        hypotheses = data.get("hypotheses")
        if type(hypotheses) is not list or not hypotheses or not all(_text(x) for x in hypotheses):
            raise ValueError("explicit hypotheses are required")
        context = data.get("context")
        if type(context) is not dict or not CONTEXT_FIELDS.issubset(context):
            raise ValueError("the complete frozen scenario context is required")
        if any(not _hash(v) for k, v in context.items() if k.endswith("_sha256")):
            raise ValueError("context checksums must be lowercase SHA-256 values")
        if any(not _text(context[k]) for k in CONTEXT_FIELDS if not k.endswith("_sha256")):
            raise ValueError("scenario, model, opaque reference and profile status are required")
        if context["profile_status"] not in {"proposed", "illustrative", "approved"}:
            raise ValueError("unknown scientific profile status")
        if not _revision(data.get("source_revision")) or not _hash(data.get("source_manifest_sha256")):
            raise ValueError("exact source revision and source-manifest SHA-256 required")
        definitions = data.get("metric_definitions")
        if (type(definitions) is not dict or not set(METRICS).issubset(definitions)
                or any(not (_text(definitions[k]) or
                            (type(definitions[k]) is dict and bool(definitions[k]))) for k in METRICS)):
            raise ValueError("every protocol metric needs an explicit definition")
        result = cls(_canonical(data))
        if claimed is not None and claimed != result.freeze_sha256:
            raise ValueError("claimed freeze checksum does not match the frozen plan")
        return result

    def to_dict(self):
        return json.loads(self._json)

    @property
    def freeze_sha256(self):
        return hashlib.sha256(self._json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RunOutcome:
    _json: str
    _findings_json: str

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict:
            raise ValueError("outcome must be a JSON object")
        encoded = _canonical(value)
        data = json.loads(encoded)
        issues = []

        def require(condition, code, detail):
            if not condition:
                issues.append(_finding(code, detail))

        require(_text(data.get("run_id")), "INVALID_RUN_ID", "A run ID is required.")
        require(data.get("policy") in ("A", "B", "C"), "INVALID_POLICY", "Policy must be A, B or C.")
        require(type(data.get("seed")) is int and data["seed"] >= 0, "INVALID_SEED", "Seed must be a nonnegative integer.")
        require(type(data.get("attempt")) is int and data["attempt"] >= 1, "INVALID_ATTEMPT", "Attempt must be an integer of at least one.")
        require(_hash(data.get("freeze_sha256")), "INVALID_FREEZE_HASH", "A frozen-plan SHA-256 is required.")
        require(data.get("execution_kind") in ("SIMULATED_MISSION", "MODEL_CHECK", "REPLAY", "SOFTWARE_TEST"),
                "INVALID_EXECUTION_KIND", "Execution kind must be explicit.")
        start, finish = _utc(data.get("started_at_utc")), _utc(data.get("finished_at_utc"))
        require(start is not None and finish is not None and finish >= start,
                "INVALID_INTERVAL", "UTC execution timestamps must form a nonnegative interval.")
        status = data.get("outcome_status")
        require(status in ("SUCCESS", "FAILED", "UNKNOWN", "TIMEOUT"), "INVALID_OUTCOME_STATUS", "Unknown outcome status.")
        require(type(data.get("termination_state")) is str and data["termination_state"] in TERMINATION_STATES,
                "INVALID_TERMINATION_STATE", "Record the final ROS mission state.")
        require(type(data.get("reason_code")) is str and (status == "SUCCESS" or _text(data.get("reason_code"))),
                "INVALID_REASON", "Non-successful outcomes require an explicit reason.")
        require(data.get("experiment_kind") in ("nominal", "sensitivity"), "INVALID_EXPERIMENT_KIND", "Experiment kind is required.")
        for name, validator in (("source_revision", _revision), ("source_manifest_sha256", _hash)):
            if name in data:
                require(validator(data[name]), "INVALID_SOURCE_IDENTITY", f"Invalid {name}.")
        predicates = data.get("predicates")
        valid_predicates = (type(predicates) is dict and set(predicates) == set(PREDICATES)
                            and all(v is None or type(v) is bool for v in predicates.values()))
        require(valid_predicates, "INVALID_PREDICATES", "Exactly four explicit boolean/null predicates are required.")
        if status == "SUCCESS":
            require(valid_predicates and all(v is True for v in predicates.values())
                    and data.get("termination_state") == "COMPLETE", "UNSUPPORTED_SUCCESS",
                    "Success requires COMPLETE and all four explicit true predicates.")
        elif valid_predicates and all(v is True for v in predicates.values()):
            require(False, "CONTRADICTORY_OUTCOME", "All four success predicates contradict a non-success outcome.")
        metrics = data.get("metrics")
        require(type(metrics) is dict and set(metrics) == set(METRICS),
                "INVALID_METRICS", "All known protocol metrics must be supplied; use null when unavailable.")
        if type(metrics) is dict:
            for name, metric in metrics.items():
                if metric is None:
                    continue
                if name == "energy_est_wh":
                    valid = (type(metric) is dict and bool(metric) and all(_text(k) and
                             (v is None or type(v) in (int, float) and v >= 0) for k, v in metric.items()))
                elif name in COUNT_METRICS:
                    valid = type(metric) is int and metric >= 0
                else:
                    valid = type(metric) in (int, float) and metric >= 0
                if name == "verified_ground_fraction" and valid:
                    valid = metric <= 1
                require(valid, "INVALID_METRIC_VALUE", f"Invalid {name}; energy must remain separated by agent.")
        artifacts = data.get("artifacts")
        require(type(artifacts) is list, "INVALID_ARTIFACTS", "An explicit artifact list is required.")
        if type(artifacts) is list:
            require(all(type(a) is dict and _text(a.get("path")) and _hash(a.get("sha256"))
                        and _text(a.get("role")) for a in artifacts), "INVALID_ARTIFACT",
                    "Artifacts require a path, SHA-256 and role.")
        refs = data.get("event_refs")
        require(type(refs) is list and all(_text(x) for x in refs) and len(set(refs)) == len(refs),
                "INVALID_EVENT_REFS", "Event references must be unique strings.")
        return cls(encoded, _canonical(issues))

    def to_dict(self):
        return json.loads(self._json)

    @property
    def validation_findings(self):
        return tuple(json.loads(self._findings_json))


def _demonstrated_success(data):
    predicates = data.get("predicates", {})
    values = [predicates.get(k) for k in PREDICATES] if type(predicates) is dict else []
    if any(value is False for value in values):
        return False
    if len(values) == 4 and all(value is True for value in values):
        return data.get("outcome_status") == "SUCCESS" and data.get("termination_state") == "COMPLETE"
    if data.get("outcome_status") in ("FAILED", "TIMEOUT"):
        return False
    return None


class ScientificBenchmark:
    """Retain all submissions; only valid, predeclared first attempts compare.

    Retries never replace a difficult first attempt. Bounds keep missing,
    unknown and invalid primary outcomes unresolved rather than calling them
    failures. Artifact findings are provided by the filesystem evidence auditor.
    """

    def __init__(self, plan):
        self.plan = plan
        self._plan = plan.to_dict()
        self._rows, self._run_ids, self._slots = [], {}, {}
        self._conflicts, self._diagnostics = set(), []

    def add(self, outcome, findings=None):
        data = outcome.to_dict()
        issues = list(outcome.validation_findings)
        if findings is None:
            issues.append(_finding("EVIDENCE_AUDIT_NOT_PERFORMED",
                                   "Pass the filesystem auditor's findings explicitly; metadata alone cannot establish evidence consistency."))
        for item in findings or ():
            if (type(item) is not dict or item.get("severity") not in ("error", "warning", "info")
                    or not _text(item.get("code")) or not _text(item.get("detail"))):
                raise ValueError("audit findings require severity, code and detail")
            issues.append(json.loads(_canonical(item)))
        run_id = data.get("run_id")
        if _text(run_id) and run_id in self._run_ids:
            index = self._run_ids[run_id]
            prior = self._rows[index]
            if prior[0]._json == outcome._json:
                retained = json.loads(prior[1])
                for issue in issues:
                    if issue not in retained:
                        retained.append(issue)
                self._rows[index] = (prior[0], _canonical(retained), prior[2])
                return False
            self._diagnostics.append({"run_id": run_id, "finding": _finding("RUN_ID_CONFLICT", "Conflicting duplicate retained as a rejected submission."),
                                      "rejected_outcome": data})
            if prior[2] is not None:
                self._conflicts.add(prior[2])
            return False
        if data.get("freeze_sha256") != self.plan.freeze_sha256:
            issues.append(_finding("FROZEN_CONTEXT_MISMATCH", "Outcome does not use this exact frozen plan."))
        if data.get("experiment_kind") != self._plan["experiment_kind"]:
            issues.append(_finding("EXPERIMENT_KIND_MISMATCH", "Nominal and sensitivity runs cannot be pooled."))
        if data.get("seed") not in self._plan["planned_seeds"] or type(data.get("seed")) is not int:
            issues.append(_finding("UNPLANNED_SEED", "The seed was not declared before execution."))
        start = _utc(data.get("started_at_utc"))
        if start is not None and start < _utc(self._plan["frozen_at_utc"]):
            issues.append(_finding("EXECUTION_PRECEDES_FREEZE", "The plan must be frozen before execution."))
        for name in ("source_revision", "source_manifest_sha256"):
            if name in data and data[name] != self._plan[name]:
                issues.append(_finding("SOURCE_IDENTITY_MISMATCH", f"{name} differs from the frozen plan."))
        if data.get("execution_kind") != "SIMULATED_MISSION":
            issues.append(_finding("NOT_MISSION_EXECUTION", "Models, software tests and replay are not integrated mission executions."))
        artifacts = data.get("artifacts", [])
        roles = {a.get("role") for a in artifacts if type(a) is dict and type(a.get("role")) is str} if type(artifacts) is list else set()
        required_roles = {"execution", "timeline"}
        if data.get("outcome_status") == "SUCCESS":
            required_roles.add("traversal")
        if not required_roles.issubset(roles) or not data.get("event_refs"):
            issues.append(_finding("EXECUTION_EVIDENCE_MISSING", "Execution/timeline evidence and event references are required; success also needs traversal evidence."))
        slot = None
        if (data.get("policy") in ("A", "B", "C") and type(data.get("seed")) is int
                and data["seed"] in self._plan["planned_seeds"] and type(data.get("attempt")) is int
                and data["attempt"] >= 1 and data.get("execution_kind") == "SIMULATED_MISSION"):
            slot = (data["policy"], data["seed"], data["attempt"])
            if slot in self._slots:
                self._conflicts.add(slot)
                issues.append(_finding("ATTEMPT_CONFLICT", "A distinct run already occupies this declared policy/seed/attempt."))
            else:
                self._slots[slot] = len(self._rows)
        index = len(self._rows)
        self._rows.append((outcome, _canonical(issues), slot))
        if _text(run_id):
            self._run_ids[run_id] = index
        return True

    def summary(self):
        policies, rows, paired = {}, [], []
        valid_primary = {}
        for policy in self._plan["policies"]:
            counts = dict(planned_n=len(self._plan["planned_seeds"]), observed_n=0, invalid_n=0,
                          successes=0, failures=0, unknowns=0, timeouts=0, missing=0)
            for seed in self._plan["planned_seeds"]:
                slot = (policy, seed, 1)
                index = self._slots.get(slot)
                if index is None:
                    counts["missing"] += 1
                    continue
                counts["observed_n"] += 1
                outcome, encoded_issues, _ = self._rows[index]
                data, issues = outcome.to_dict(), json.loads(encoded_issues)
                valid = not any(x["severity"] == "error" for x in issues) and slot not in self._conflicts
                if not valid:
                    counts["invalid_n"] += 1
                    continue
                success = _demonstrated_success(data)
                counts["successes" if success is True else "failures" if success is False else "unknowns"] += 1
                if data.get("outcome_status") == "TIMEOUT":
                    counts["timeouts"] += 1
                valid_primary[(policy, seed)] = all(type(data["predicates"][k]) is bool for k in PREDICATES) and success is not None
            unresolved = counts["unknowns"] + counts["missing"] + counts["invalid_n"]
            counts["success_denominator"] = counts["planned_n"]
            counts["success_lower_bound"] = counts["successes"] / counts["planned_n"]
            counts["success_upper_bound"] = (counts["successes"] + unresolved) / counts["planned_n"]
            counts["retry_rows"] = sum(1 for _, _, slot in self._rows if slot is not None and slot[0] == policy and slot[2] > 1)
            policies[policy] = counts
        for seed in self._plan["planned_seeds"]:
            if all(valid_primary.get((policy, seed), False) for policy in self._plan["policies"]):
                paired.append(seed)
        for index, (outcome, encoded_issues, slot) in enumerate(self._rows):
            issues = json.loads(encoded_issues)
            if slot in self._conflicts:
                issues.append(_finding("ATTEMPT_CONFLICT", "Conflicting identity prevents selecting this attempt."))
            valid = slot is not None and not any(x["severity"] == "error" for x in issues)
            primary = slot is not None and slot[2] == 1 and self._slots.get(slot) == index
            rows.append({"outcome": outcome.to_dict(), "findings": issues,
                         "primary_attempt": primary, "valid": valid, "eligible": valid and primary,
                         "mission_success": _demonstrated_success(outcome.to_dict()) if valid else None})
        return {"schema_version": "1.0.0", "benchmark_id": self._plan["benchmark_id"],
                "freeze_sha256": self.plan.freeze_sha256, "experiment_kind": self._plan["experiment_kind"],
                "scientific_approval": False, "evidence_assurance": "consistency_and_traceability_only",
                "comparison_ready": len(paired) == len(self._plan["planned_seeds"]),
                "paired_complete_seeds": paired, "policies": policies,
                "retained_rows": rows, "diagnostics": json.loads(_canonical(self._diagnostics))}
