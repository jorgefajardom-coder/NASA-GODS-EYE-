"""Read exported execution evidence without running a mission or granting approval."""

from datetime import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

from .benchmark import PREDICATES


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _json(text):
    def invalid_constant(_):
        raise ValueError("nonfinite JSON")
    return json.loads(text, parse_constant=invalid_constant)


def _digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _artifact_path(root, raw):
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise ValueError("artifact paths must be canonical relative POSIX paths")
    relative = PurePosixPath(raw)
    if (relative.is_absolute() or PureWindowsPath(raw).drive or ".." in relative.parts
            or relative.as_posix() != raw or any(":" in part for part in relative.parts)):
        raise ValueError("artifact path escapes or is not canonical")
    if any(part.casefold() in {"reference", ".git", ".env"} for part in relative.parts):
        raise ValueError("hidden evaluator/reference or private paths are not evidence inputs")
    path = root.joinpath(*relative.parts).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("artifact must be a file within the supplied run directory")
    if any(part.casefold() in {"reference", ".git", ".env"} for part in path.relative_to(root).parts):
        raise ValueError("resolved artifact points into private or evaluator-reference content")
    if path.suffix.lower() not in {".json", ".jsonl", ".csv", ".txt", ".log"}:
        raise ValueError("audit exported text evidence, never reference rasters or executable files")
    return path


def _timeline(path):
    if path.suffix.lower() == ".jsonl":
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    yield _json(line)
    else:
        payload = _json(path.read_text(encoding="utf-8"))
        entries = payload.get("events") if isinstance(payload, dict) else payload
        if not isinstance(entries, list):
            raise ValueError("timeline must be JSON events or JSONL")
        yield from entries


class EvidenceAudit:
    """Consistency and traceability only; metadata cannot prove physical execution."""

    def audit(self, plan, outcome, run_directory):
        declaration, record = plan.to_dict(), outcome.to_dict()
        findings = []

        def add(code, detail, severity="error"):
            findings.append({"severity": severity, "code": code, "detail": detail})

        if record.get("freeze_sha256") != plan.freeze_sha256:
            add("FROZEN_CONTEXT_MISMATCH", "The outcome does not retain this exact frozen protocol.")
        if record.get("experiment_kind") != declaration["experiment_kind"]:
            add("EXPERIMENT_KIND_MISMATCH", "Nominal and sensitivity experiments cannot be pooled.")
        if record.get("policy") not in declaration["policies"] or record.get("seed") not in declaration["planned_seeds"]:
            add("UNPLANNED_POLICY_OR_SEED", "Policy and seed must be declared before execution.")
        if record.get("execution_kind") != "SIMULATED_MISSION":
            add("NOT_MISSION_EVIDENCE", "Model checks, software tests and replay are not new mission executions.")
            return tuple(findings)
        try:
            root = Path(run_directory).resolve(strict=True)
            if not root.is_dir() or any(part.casefold() == "reference" for part in root.parts):
                raise ValueError
        except (OSError, ValueError):
            add("RUN_DIRECTORY_INVALID", "Supply an existing execution-evidence directory outside the evaluator reference.")
            return tuple(findings)
        try:
            frozen = datetime.fromisoformat(declaration["frozen_at_utc"].replace("Z", "+00:00"))
            started = datetime.fromisoformat(record["started_at_utc"].replace("Z", "+00:00"))
            if started < frozen:
                add("EXECUTION_BEFORE_FREEZE", "Execution predates its declared experiment freeze.")
        except (KeyError, TypeError, ValueError):
            add("FREEZE_TIME_UNVERIFIABLE", "Explicit UTC freeze and execution times are required.")
        for key in ("source_revision", "source_manifest_sha256"):
            if record.get(key) != declaration.get(key):
                add("SOURCE_IDENTITY_MISMATCH", f"The execution must retain the frozen {key}.")
        command = record.get("command")
        if not isinstance(command, list) or not command or any(not isinstance(x, str) or not x for x in command):
            add("EXECUTION_COMMAND_MISSING", "Record the actual execution command and arguments.")
        if not isinstance(record.get("environment"), dict) or not record["environment"]:
            add("EXECUTION_ENVIRONMENT_MISSING", "Record the execution environment and software versions.")

        artifacts = record.get("artifacts")
        if not isinstance(artifacts, list):
            add("ARTIFACTS_INVALID", "Execution artifacts must be a list.")
            return tuple(findings)
        verified = {}
        roles = {"execution", "timeline", "traversal", "metrics", "environment", "configuration", "diagnostic"}
        seen = set()
        for item in artifacts:
            if not isinstance(item, dict) or item.get("role") not in roles:
                add("ARTIFACT_ROLE_INVALID", "Each artifact needs a supported evidence role.")
                continue
            role, relative = item["role"], item.get("path")
            try:
                path = _artifact_path(root, relative)
                key = (role, path)
                if key in seen:
                    add("DUPLICATE_ARTIFACT", "An artifact role/path was listed more than once.")
                    continue
                seen.add(key)
                expected = item.get("sha256")
                if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                    raise ValueError("artifact requires a lowercase SHA-256")
                if _digest(path) != expected:
                    add("ARTIFACT_HASH_MISMATCH", f"Artifact content does not match its declared hash: {relative}")
                    continue
                verified.setdefault(role, []).append(path)
            except (OSError, ValueError):
                add("ARTIFACT_UNAVAILABLE_OR_UNSAFE", f"Artifact is missing, unsafe or malformed: {relative}")

        events, last_seq = {}, 0
        if not verified.get("timeline"):
            add("TIMELINE_EVIDENCE_MISSING", "A hashed event timeline is required.")
        for path in verified.get("timeline", []):
            try:
                for event in _timeline(path):
                    if not isinstance(event, dict) or event.get("run_id") != record.get("run_id"):
                        add("EVENT_RUN_MISMATCH", "Timeline events must belong to this execution.")
                        continue
                    event_id, seq = event.get("event_id"), event.get("seq")
                    if not isinstance(event_id, str) or not event_id or type(seq) is not int or seq < 1:
                        add("EVENT_ID_INVALID", "Each event needs an ID and a positive integer sequence.")
                        continue
                    if event_id in events:
                        if events[event_id] != event:
                            add("EVENT_ID_CONFLICT", "An event ID identifies conflicting payloads.")
                        continue  # Identical at-least-once deliveries are idempotent.
                    if seq != last_seq + 1:
                        add("EVENT_SEQUENCE_INCOMPLETE", "The exported timeline must retain ordered events without gaps.")
                    events[event_id], last_seq = event, seq
            except (OSError, ValueError, TypeError):
                add("TIMELINE_INVALID", "Timeline must be finite JSON/JSONL execution events.")
        refs = record.get("event_refs")
        if not isinstance(refs, list) or not refs:
            add("EVENT_REFERENCES_MISSING", "An execution outcome must reference recorded event IDs.")
        elif any(not isinstance(ref, str) or ref not in events for ref in refs):
            add("EVENT_REFERENCE_UNRESOLVED", "An outcome references an event absent from the verified timeline.")

        def read_records(role):
            result = []
            for path in verified.get(role, []):
                try:
                    value = _json(path.read_text(encoding="utf-8"))
                    if not isinstance(value, dict) or value.get("run_id") != record.get("run_id"):
                        raise ValueError
                    if (not isinstance(value.get("event_refs"), list) or not value["event_refs"]
                            or any(ref not in events for ref in value["event_refs"])):
                        add("EVIDENCE_EVENT_UNRESOLVED", f"{role} evidence requires resolved event references.")
                    result.append(value)
                except (OSError, ValueError, TypeError):
                    add("EVIDENCE_RECORD_INVALID", f"{role} evidence must be a JSON object for this run.")
            return result

        execution = read_records("execution")
        if not execution:
            add("EXECUTION_EVIDENCE_MISSING", "A hashed execution declaration is required.")
        elif len(execution) != 1:
            add("AMBIGUOUS_EXECUTION_EVIDENCE", "Version 1 requires one aggregate execution declaration per outcome.")
        for item in execution:
            if item.get("execution_kind") != "SIMULATED_MISSION":
                add("EXECUTION_KIND_MISMATCH", "The evidence must describe an actual simulated mission execution.")
            if item.get("predicates") != record.get("predicates"):
                add("PREDICATE_EVIDENCE_MISMATCH", "Outcome predicates differ from their execution evidence.")
        metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
        predicates = record.get("predicates") if isinstance(record.get("predicates"), dict) else {}
        claimed_success = all(predicates.get(key) is True for key in PREDICATES)
        traversal = read_records("traversal")
        if len(traversal) > 1:
            add("AMBIGUOUS_TRAVERSAL_EVIDENCE", "Version 1 requires one distance-weighted aggregate traversal record.")
        if claimed_success and not traversal:
            add("TRAVERSAL_EVIDENCE_MISSING", "Success needs execution-time ground traversal evidence.")
        for item in traversal:
            total, checked = item.get("executed_ground_distance_m"), item.get("verified_ground_distance_m")
            if not _finite(total) or not _finite(checked) or checked > total:
                add("TRAVERSAL_DISTANCES_INVALID", "Verified executed distance must be within total executed ground distance.")
                continue
            fraction = metrics.get("verified_ground_fraction")
            if total == 0:
                if fraction is not None:
                    add("UNDEFINED_VERIFIED_FRACTION", "Zero ground distance has no verified-ground fraction.")
                if metrics.get("unsafe_step_count") == 0:
                    add("UNOBSERVED_UNSAFE_ZERO", "No ground traversal cannot establish an observed unsafe-step zero.")
            elif fraction is not None and (not _finite(fraction) or not math.isclose(fraction, checked / total, rel_tol=1e-6, abs_tol=1e-9)):
                add("VERIFIED_FRACTION_MISMATCH", "Reported verification fraction must be distance-weighted execution evidence.")
            count = item.get("unsafe_step_count")
            if count is not None and (type(count) is not int or count < 0):
                add("UNSAFE_COUNT_INVALID", "Unsafe-step counts must be nonnegative integer observations or null.")
            if metrics.get("unsafe_step_count") is not None and metrics["unsafe_step_count"] != count:
                add("UNSAFE_COUNT_MISMATCH", "The metric and traversal evidence disagree on unsafe steps.")
            if count == 0 and item.get("all_executed_steps_checked") is not True:
                add("UNOBSERVED_UNSAFE_ZERO", "A zero unsafe-step count needs every executed step checked.")
            if claimed_success and (total <= 0 or checked != total or count != 0
                                    or item.get("all_executed_steps_checked") is not True):
                add("TRAVERSAL_NOT_VERIFIED", "Successful completion needs a fully checked executed ground route.")
            if item.get("model_id") != declaration["context"]["model_id"]:
                add("TRAVERSAL_MODEL_MISMATCH", "Traversal evidence must retain the frozen resource/verification model.")
        if claimed_success and not any(event.get("event_type") == "MISSION_STATE_CHANGED"
                                       and event.get("new_state") == "COMPLETE" for event in events.values()):
            add("SUCCESS_EVENT_MISSING", "Success needs an explicit completed-mission event in the recorded timeline.")
        unavailable = record.get("metrics_unavailable", {})
        for name, value in metrics.items():
            if value is None and (not isinstance(unavailable, dict) or not isinstance(unavailable.get(name), str)
                                  or not unavailable[name].strip()):
                add("METRIC_UNAVAILABLE_REASON_MISSING", f"Explain unavailable metric {name}; do not replace null with zero.", "warning")
        return tuple(findings)
