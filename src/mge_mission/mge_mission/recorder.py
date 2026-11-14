"""Append-only public execution records; no ROS subscriptions or inferred execution."""

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path

from .benchmark import METRICS, PREDICATES, RunOutcome, _canonical
from .models import CostEstimate
from .types import MissionEvent, MissionEvidence, ObservedTask, Point, TaskEvidence


JOURNAL_VERSION = "1.0.0"


def _journal_path(path):
    result = Path(path).resolve()
    if result.suffix.lower() != ".jsonl" or any(
            part.casefold() in {"reference", ".git", ".env"} for part in result.parts):
        raise ValueError("Journal must be a public .jsonl file outside private/reference paths")
    return result


def _lock_journal(stream):
    """Hold one writer for the lifetime of this open descriptor, including recovery."""
    if os.name == "nt":
        import msvcrt
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Expected a finite nonnegative number")


@dataclass(frozen=True)
class TraversalRecord:
    """One actually executed ground step, checked against the public map/model."""

    evidence_id: str
    run_id: str
    agent_id: str
    map_version: int
    route_id: str
    event_id: str
    distance_m: float
    safe_under_model: bool | None


@dataclass(frozen=True)
class ExecutedCost:
    """Model cost of a completed interval, never a planned route allocation."""

    evidence_id: str
    run_id: str
    agent_id: str
    kind: str
    event_id: str
    phase: str
    started_sim_s: float
    finished_sim_s: float
    cost: CostEstimate


@dataclass(frozen=True)
class TraversalClosure:
    """Executor's explicit total, needed to establish that no steps were omitted."""

    evidence_id: str
    run_id: str
    event_id: str
    executed_step_count: int
    executed_ground_distance_m: float


class EvidenceRecorder:
    """Single-writer recorder. Export once to a new directory; retain raw inputs.

    Callers must feed public execution observations, not planner predictions.
    Without journal_path records live in memory until export. An optional journal
    durably records each accepted input before memory changes. Close a writer
    before recovery; recovery retains its original identity and execution kind.
    """

    def __init__(self, run_id, model_id, *, execution_kind, journal_path=None):
        if (not isinstance(run_id, str) or not run_id.strip()
                or not isinstance(model_id, str) or not model_id.strip() or execution_kind not in {
                "SIMULATED_MISSION", "MODEL_CHECK", "REPLAY", "SOFTWARE_TEST"}):
            raise ValueError("Explicit run/model identity and execution kind are required")
        self.run_id, self.model_id, self.execution_kind = run_id, model_id, execution_kind
        self._events, self._records = {}, {}
        self._predicates = {key: None for key in PREDICATES}
        self._sealed = False
        self._closed = self._journal_failed = self._recovered = False
        self._journal_stream = None
        self._journal_seq, self._journal_previous, self._journal_size = 0, "0" * 64, 0
        if journal_path is not None:
            path = _journal_path(journal_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            stream = path.open("x+b", buffering=0)
            try:
                _lock_journal(stream)
                self._journal_stream = stream
                self._persist("identity", {"schema_version": JOURNAL_VERSION, "run_id": run_id,
                                          "model_id": model_id, "execution_kind": execution_kind})
            except BaseException:
                stream.close()
                raise

    def _persist(self, kind, payload):
        stream = self._journal_stream
        if stream is None:
            return
        body = {"seq": self._journal_seq, "previous_sha256": self._journal_previous,
                "kind": kind, "payload": payload}
        digest = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
        raw = (_canonical({**body, "sha256": digest}) + "\n").encode("utf-8")
        try:
            # Locks serialize cooperating writers; size also catches external edits.
            if os.fstat(stream.fileno()).st_size != self._journal_size:
                raise OSError("Journal changed outside its active writer")
            stream.seek(0, os.SEEK_END)
            if stream.write(raw) != len(raw):
                raise OSError("Incomplete journal write")
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            # A failed flush may have written some/all bytes; never retry blindly.
            self._journal_failed = True
            raise
        self._journal_seq += 1
        self._journal_previous, self._journal_size = digest, self._journal_size + len(raw)

    def close(self):
        """Release the journal lock; closed recorders cannot accept inputs or export."""
        if self._journal_stream is not None:
            self._journal_stream.close()
            self._journal_stream = None
        self._closed = True

    def __enter__(self):
        if self._closed:
            raise ValueError("Recorder is closed")
        return self

    def __exit__(self, *exc):
        self.close()

    @classmethod
    def recover(cls, journal_path):
        """Validate and resume the same journal without altering invalid sources.

        The exclusive writer must have closed or exited. A valid terminal seal
        restores a sealed recorder, not permission to publish another outcome.
        Hash chaining detects accidental damage, not a trusted digital signature.
        """
        path = _journal_path(journal_path)
        stream = path.open("r+b", buffering=0)
        try:
            _lock_journal(stream)
            stream.seek(0)
            raw = stream.read()
            if not raw or not raw.endswith(b"\n"):
                raise ValueError("Empty or truncated journal")
            previous, instance, count = "0" * 64, None, 0
            for seq, line in enumerate(raw.splitlines(keepends=True)):
                entry = json.loads(line)
                if not isinstance(entry, dict) or set(entry) != {
                        "seq", "previous_sha256", "kind", "payload", "sha256"}:
                    raise ValueError("Invalid journal entry shape")
                body = {key: value for key, value in entry.items() if key != "sha256"}
                digest = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
                if (type(entry["seq"]) is not int or entry["seq"] != seq
                        or entry["previous_sha256"] != previous or entry["sha256"] != digest
                        or (_canonical(entry) + "\n").encode("utf-8") != line):
                    raise ValueError("Corrupt or unordered journal entry")
                payload, kind = entry["payload"], entry["kind"]
                if seq == 0:
                    if kind != "identity" or set(payload) != {
                            "schema_version", "run_id", "model_id", "execution_kind"}:
                        raise ValueError("Journal must begin with its explicit identity")
                    if payload["schema_version"] != JOURNAL_VERSION:
                        raise ValueError("Unsupported journal version")
                    instance = cls(payload["run_id"], payload["model_id"],
                                   execution_kind=payload["execution_kind"])
                else:
                    instance._restore(kind, payload)
                previous, count = digest, seq + 1
            instance._journal_stream = stream
            instance._journal_seq, instance._journal_previous, instance._journal_size = count, previous, len(raw)
            instance._recovered = True
            return instance
        except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            stream.close()
            raise ValueError("Corrupt journal") from exc
        except BaseException:
            stream.close()
            raise

    def _restore(self, kind, payload):
        self._open()
        if kind == "event":
            before = len(self._events)
            self.record_event(MissionEvent(**payload))
            if len(self._events) != before + 1:
                raise ValueError("Duplicate accepted journal input")
        elif kind == "evidence":
            record = dict(payload)
            record_type, refs = record.pop("record_type"), record.pop("event_refs")
            before = len(self._records)
            if record_type == "ObservedTask":
                record["position"] = Point(**record["position"])
                self.record_discovery(ObservedTask(**record), *refs)
            elif record_type == "TaskEvidence":
                self.record_task_completion(TaskEvidence(**record), *refs)
            elif record_type == "TraversalRecord":
                value = TraversalRecord(**record)
                if refs != [value.event_id]:
                    raise ValueError("Traversal journal references disagree")
                self.record_traversal(value)
            elif record_type == "ExecutedCost":
                record["cost"] = CostEstimate(**record["cost"])
                value = ExecutedCost(**record)
                if refs != [value.event_id]:
                    raise ValueError("Cost journal references disagree")
                self.record_cost(value)
            elif record_type == "TraversalClosure":
                value = TraversalClosure(**record)
                if refs != [value.event_id]:
                    raise ValueError("Closure journal references disagree")
                self.close_traversal(value)
            elif record_type == "MissionEvidence":
                self.record_predicates(MissionEvidence(**record), *refs)
            else:
                raise ValueError("Unknown journal evidence type")
            if len(self._records) != before + 1:
                raise ValueError("Duplicate accepted journal input")
        elif kind == "seal":
            if (not isinstance(payload, dict) or set(payload) != {"metadata_sha256"}
                    or not isinstance(payload["metadata_sha256"], str)
                    or len(payload["metadata_sha256"]) != 64
                    or any(x not in "0123456789abcdef" for x in payload["metadata_sha256"])):
                raise ValueError("Invalid journal seal")
            self._sealed = True
        else:
            raise ValueError("Unknown journal entry type")

    def _open(self):
        if self._closed or self._journal_failed:
            raise ValueError("Recorder is closed or its journal failed; recover the journal explicitly")
        if self._sealed:
            raise ValueError("Recorder has been exported and sealed")

    def record_event(self, event: MissionEvent):
        self._open()
        if not isinstance(event, MissionEvent) or event.run_id != self.run_id:
            raise ValueError("Expected a MissionEvent for this run")
        data = asdict(event)
        _canonical(data)
        if event.event_id in self._events:
            if self._events[event.event_id] != data:
                raise ValueError("Conflicting event delivery")
            return
        if not event.event_id or type(event.seq) is not int or event.seq != len(self._events) + 1:
            raise ValueError("Events must arrive in sequence, starting at one")
        if event.timestamp_sim_s is not None:
            _number(event.timestamp_sim_s)
            times = [x["timestamp_sim_s"] for x in self._events.values()
                     if x["timestamp_sim_s"] is not None]
            if times and event.timestamp_sim_s < times[-1]:
                raise ValueError("Simulation time cannot move backwards within a run")
        self._persist("event", data)
        self._events[event.event_id] = data
        self._predicates = {key: None for key in PREDICATES}

    def _record(self, record, refs, *, evidence_id=None):
        self._open()
        data = asdict(record)
        _canonical(data)
        evidence_id = evidence_id or getattr(record, "evidence_id", "")
        if record.run_id != self.run_id or not evidence_id:
            raise ValueError("Evidence needs a unique identity for this run")
        if not refs or any(ref not in self._events for ref in refs):
            raise ValueError("Evidence must reference already recorded events")
        payload = {"record_type": type(record).__name__, "event_refs": list(refs), **data}
        previous = self._records.get(evidence_id)
        if previous is not None:
            if previous != payload:
                raise ValueError("Conflicting evidence delivery")
            return False
        self._persist("evidence", payload)
        self._records[evidence_id] = payload
        return True

    def record_discovery(self, task: ObservedTask, event_id: str):
        if not isinstance(task, ObservedTask):
            raise ValueError("Expected public ObservedTask")
        event = self._events.get(event_id, {})
        if (event.get("event_type") != "TASK_DISCOVERED" or task.task_id != event.get("task_id")
                or task.map_version != event.get("map_version")
                or task.discovery_id != event.get("causality_id")):
            raise ValueError("Discovery must match a public core discovery event")
        self._record(task, [event_id], evidence_id=task.discovery_id)

    def record_task_completion(self, evidence: TaskEvidence, event_id: str):
        if not isinstance(evidence, TaskEvidence):
            raise ValueError("Expected TaskEvidence")
        event = self._events.get(event_id, {})
        if (event.get("event_type") != "TASK_STATE_CHANGED" or event.get("new_state") != "DONE"
                or evidence.task_id != event.get("task_id")
                or evidence.route_id != event.get("route_id")
                or evidence.map_version != event.get("map_version")
                or evidence.timestamp_sim_s != event.get("timestamp_sim_s")
                or evidence.evidence_id != event.get("causality_id")):
            raise ValueError("Completion requires the core's observed DONE event")
        self._record(evidence, [event_id])

    def record_traversal(self, record: TraversalRecord):
        if not isinstance(record, TraversalRecord):
            raise ValueError("Expected TraversalRecord")
        _number(record.distance_m)
        if not record.agent_id or record.distance_m <= 0 or (
                record.safe_under_model is not None and type(record.safe_under_model) is not bool):
            raise ValueError("Traversal requires positive distance and a tri-state check")
        event = self._events.get(record.event_id, {})
        if (not record.route_id or record.route_id != event.get("route_id")
                or record.map_version != event.get("map_version")
                or record.agent_id != event.get("agent_id")):
            raise ValueError("Traversal must retain the observed event's agent, route and map")
        self._record(record, [record.event_id])

    def record_cost(self, record: ExecutedCost):
        if not isinstance(record, ExecutedCost) or not isinstance(record.cost, CostEstimate):
            raise ValueError("Expected ExecutedCost with CostEstimate")
        _number(record.started_sim_s)
        _number(record.finished_sim_s)
        if (not record.agent_id or record.kind not in {"human", "rover", "drone"}
                or record.phase not in {"movement", "service", "wait"}
                or record.finished_sim_s <= record.started_sim_s
                or not math.isclose(record.cost.time_s, record.finished_sim_s - record.started_sim_s)):
            raise ValueError("Cost must describe one completed movement/service/wait interval")
        if (record.kind == "human") != (record.cost.oxygen_l is not None):
            raise ValueError("Only human costs carry oxygen")
        event = self._events.get(record.event_id, {})
        if (event.get("agent_id") != record.agent_id or event.get("timestamp_sim_s") is None
                or record.finished_sim_s > event["timestamp_sim_s"]):
            raise ValueError("Completion event must observe this agent after the interval")
        for item in self._records.values():
            if item["record_type"] != "ExecutedCost" or item["agent_id"] != record.agent_id:
                continue
            if item["kind"] != record.kind:
                raise ValueError("Agent kind cannot change")
            if item["evidence_id"] != record.evidence_id and max(
                    item["started_sim_s"], record.started_sim_s) < min(
                        item["finished_sim_s"], record.finished_sim_s):
                raise ValueError("Executed intervals must not overlap or double-count costs")
        self._record(record, [record.event_id])

    def close_traversal(self, record: TraversalClosure):
        if not isinstance(record, TraversalClosure):
            raise ValueError("Expected TraversalClosure")
        _number(record.executed_ground_distance_m)
        if type(record.executed_step_count) is not int or record.executed_step_count < 0:
            raise ValueError("Executed step count must be a nonnegative integer")
        if record.event_id != next(reversed(self._events), None):
            raise ValueError("Traversal closure must bind to the latest execution event")
        self._record(record, [record.event_id])

    def record_predicates(self, evidence: MissionEvidence, event_id: str):
        if not isinstance(evidence, MissionEvidence):
            raise ValueError("Expected MissionEvidence")
        event = self._events.get(event_id, {})
        _number(evidence.timestamp_sim_s)
        if (evidence.route_id != event.get("route_id") or evidence.map_version != event.get("map_version")
                or evidence.timestamp_sim_s != event.get("timestamp_sim_s")):
            raise ValueError("Predicate evidence must bind to the observed route/map/time")
        if (evidence.evidence_id not in self._records
                and event_id != next(reversed(self._events), None)):
            raise ValueError("Predicate snapshots must describe the latest recorded event")
        for key in PREDICATES:
            value = getattr(evidence, key)
            if value is not None and type(value) is not bool:
                raise ValueError("Predicates are boolean or unknown")
        if self._record(evidence, [event_id]):
            # Each record is a full snapshot, so later unknowns invalidate earlier claims.
            self._predicates = {key: getattr(evidence, key) for key in PREDICATES}

    def export(self, directory, metadata):
        """Export hashed raw records and an audit-compatible outcome, exclusively.

        Metadata supplies actual command/environment, frozen identity and UTC times.
        Unimplemented metrics stay null with reasons. No status is inferred from a plan.
        """
        self._open()
        if not self._events:
            raise ValueError("Cannot export an execution without events")
        data = json.loads(_canonical(metadata))
        reserved = {"run_id", "execution_kind", "predicates", "metrics", "artifacts", "event_refs",
                    "metrics_unavailable"}
        if reserved.intersection(data):
            raise ValueError("Metadata cannot override recorded evidence")
        events, records = list(self._events.values()), list(self._records.values())
        steps = [x for x in records if x["record_type"] == "TraversalRecord"]
        costs = [x for x in records if x["record_type"] == "ExecutedCost"]
        total = sum(x["distance_m"] for x in steps)
        verified = sum(x["distance_m"] for x in steps if x["safe_under_model"] is True)
        closures = [x for x in records if x["record_type"] == "TraversalClosure"]
        closure = closures[-1] if closures else {}
        covered = (closure.get("executed_step_count") == len(steps)
                   and math.isclose(closure.get("executed_ground_distance_m", -1), total)
                   and closure.get("event_id") == events[-1]["event_id"])
        checked = covered and bool(steps) and all(x["safe_under_model"] is not None for x in steps)
        unsafe = sum(x["safe_under_model"] is False for x in steps) if checked else None
        metrics = {key: None for key in METRICS}
        metrics.update(verified_ground_fraction=verified / total if covered and total else None,
                       unsafe_step_count=unsafe)
        times = [x["timestamp_sim_s"] for x in events]
        complete_times = all(x is not None for x in times)
        if costs:
            energy = {}
            coverage = {}
            for agent in sorted({x["agent_id"] for x in costs}):
                intervals = sorted((x for x in costs if x["agent_id"] == agent),
                                   key=lambda x: x["started_sim_s"])
                coverage[agent] = (complete_times and intervals[0]["started_sim_s"] == times[0]
                                   and intervals[-1]["finished_sim_s"] == times[-1]
                                   and all(a["finished_sim_s"] == b["started_sim_s"]
                                           for a, b in zip(intervals, intervals[1:])))
                energy[agent] = (sum(x["cost"]["energy_wh"] for x in intervals)
                                 if coverage[agent] else None)
            metrics["energy_est_wh"] = energy
            human = [x for x in costs if x["kind"] == "human"]
            metrics["oxygen_est_l"] = (sum(x["cost"]["oxygen_l"] for x in human)
                if human and all(coverage[x["agent_id"]] for x in human) else None)
        if complete_times:
            metrics["mission_duration_s"] = times[-1] - times[0]
        refs = [x["event_id"] for x in events]
        data.update(run_id=self.run_id, execution_kind=self.execution_kind,
                    predicates=dict(self._predicates), metrics=metrics, artifacts=[], event_refs=refs,
                    metrics_unavailable={key: "No complete public execution measurement recorded."
                                         for key, value in metrics.items() if value is None})
        # Costs describe recorded intervals only; their coverage is explicitly retained.
        data["cost_coverage"] = "whole_recorded_timeline_required_per_agent; raw intervals retained"
        for agent, value in (metrics["energy_est_wh"] or {}).items():
            if value is None:
                data["metrics_unavailable"][f"energy_est_wh.{agent}"] = "Incomplete interval coverage."
        state = next((x["new_state"] for x in reversed(events)
                      if x["event_type"] == "MISSION_STATE_CHANGED" and x["new_state"]), None)
        if state is not None and data.get("termination_state") != state:
            raise ValueError("Termination must agree with the final recorded event state")
        if data.get("outcome_status") == "SUCCESS" and (
                state != "COMPLETE" or not checked or not total or verified != total or unsafe != 0):
            raise ValueError("Success requires completely verified executed ground traversal")
        if not data.get("command") or not data.get("environment"):
            raise ValueError("Actual execution command and environment are required")
        outcome = RunOutcome.from_dict(data)
        if outcome.validation_findings:
            raise ValueError(f"Invalid outcome metadata/evidence: {outcome.validation_findings}")
        root = Path(directory).resolve()
        if any(x.casefold() in {"reference", ".git", ".env"} for x in root.parts):
            raise ValueError("Evidence exports must stay outside private/reference paths")
        root.mkdir(parents=True, exist_ok=False)
        journal_raw = None
        if self._journal_stream is not None:
            self._persist("seal", {"metadata_sha256": hashlib.sha256(
                _canonical(metadata).encode("utf-8")).hexdigest()})
            # A partial export remains sealed: never publish a second outcome
            # under the same execution identity after ambiguous filesystem I/O.
            self._sealed = True
            self._journal_stream.seek(0)
            journal_raw = self._journal_stream.read()
            data["recovered_from_journal"] = self._recovered
        payloads = {
            "timeline.jsonl": ("timeline", "".join(_canonical(x) + "\n" for x in events)),
            "records.json": ("diagnostic", _canonical({"run_id": self.run_id, "records": records})),
            "execution.json": ("execution", _canonical({"run_id": self.run_id,
                "execution_kind": self.execution_kind, "event_refs": refs,
                "predicates": self._predicates})),
        }
        if steps:
            payloads["traversal.json"] = ("traversal", _canonical({"run_id": self.run_id,
                "model_id": self.model_id, "event_refs": list(dict.fromkeys(x["event_id"] for x in steps)),
                "executed_ground_distance_m": total, "verified_ground_distance_m": verified,
                "unsafe_step_count": unsafe, "all_executed_steps_checked": checked}))
        if journal_raw is not None:
            name = "recorder_journal.jsonl"
            with (root / name).open("xb") as stream:
                stream.write(journal_raw)
            data["artifacts"].append({"path": name, "role": "diagnostic",
                                      "sha256": hashlib.sha256(journal_raw).hexdigest()})
        for name, (role, content) in payloads.items():
            raw = (content + "\n").encode("utf-8")
            with (root / name).open("xb") as stream:
                stream.write(raw)
            data["artifacts"].append({"path": name, "role": role,
                                      "sha256": hashlib.sha256(raw).hexdigest()})
        with (root / "outcome.json").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(data, indent=2, allow_nan=False) + "\n")
        self._sealed = True
        return RunOutcome.from_dict(data)
