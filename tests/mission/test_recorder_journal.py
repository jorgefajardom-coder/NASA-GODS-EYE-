"""Durability software fixtures; no fixture is a submitted mission outcome."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from mge_mission.audit import EvidenceAudit
from mge_mission.benchmark import CONTEXT_FIELDS, METRICS, FrozenBenchmarkPlan, _canonical
from mge_mission.models import CostEstimate
from mge_mission.recorder import EvidenceRecorder, ExecutedCost, TraversalClosure, TraversalRecord
from mge_mission.types import MissionEvent, MissionEvidence, ObservedTask, Point, TaskEvidence


def event(seq=1, time=0, state="ACTIVE"):
    return MissionEvent("journal-fixture", f"e{seq}", seq, "public-observation", "MISSION_STATE_CHANGED",
                        "", "human_1", 1, "route", "", state, "", "", time)


def recorder(path=None, *, kind="SOFTWARE_TEST"):
    return EvidenceRecorder("journal-fixture", "fixture-model", execution_kind=kind, journal_path=path)


def metadata(status="UNKNOWN"):
    return dict(policy="A", seed=7, attempt=1, freeze_sha256="a" * 64,
                started_at_utc="2026-11-14T08:00:00Z", finished_at_utc="2026-11-14T08:01:00Z",
                outcome_status=status, termination_state="COMPLETE", reason_code="FIXTURE",
                experiment_kind="nominal", source_revision="b" * 40,
                source_manifest_sha256="c" * 64, command=["pytest-fixture"],
                environment={"kind": "software-test-fixture"})


def populate(value, *, known=True):
    value.record_event(event())
    value.record_event(event(2, 10, "COMPLETE"))
    value.record_traversal(TraversalRecord("step", "journal-fixture", "human_1", 1,
                                         "route", "e2", 5, True if known else None))
    value.close_traversal(TraversalClosure("closure", "journal-fixture", "e2", 1, 5))
    value.record_cost(ExecutedCost("cost", "journal-fixture", "human_1", "human", "e2",
                                  "movement", 0, 10, CostEstimate(10, 2, 1)))
    value.record_predicates(MissionEvidence("pred", "journal-fixture", 1, "route", 10,
                                           True, True, True, True) if known else
                            MissionEvidence("pred", "journal-fixture", 1, "route", 10), "e2")


def compare_evidence(left, right):
    assert left._events == right._events
    assert left._records == right._records
    assert left._predicates == right._predicates
    assert (left.run_id, left.model_id, left.execution_kind) == (right.run_id, right.model_id, right.execution_kind)


def active_bytes(value):
    # Windows byte locks deliberately deny readers on other descriptors.
    value._journal_stream.seek(0)
    return value._journal_stream.read()


def test_recovery_restores_exact_inputs_unknowns_and_original_identity(tmp_path):
    path = tmp_path / "journal.jsonl"
    original = recorder(path, kind="REPLAY")
    populate(original, known=False)
    original.close()
    before = path.read_bytes()
    with EvidenceRecorder.recover(path) as recovered:
        compare_evidence(original, recovered)
        assert active_bytes(recovered) == before
        assert recovered.execution_kind == "REPLAY"
        outcome = recovered.export(tmp_path / "run", metadata()).to_dict()
        assert all(value is None for value in outcome["predicates"].values())
        assert outcome["metrics"]["unsafe_step_count"] is None
        assert outcome["metrics"]["energy_est_wh"] == {"human_1": 2}
        assert outcome["recovered_from_journal"] is True
        assert outcome["execution_kind"] == "REPLAY"


def test_recovered_recorder_resumes_without_new_identity_or_duplicate_costs(tmp_path):
    path = tmp_path / "journal.jsonl"
    with recorder(path) as original:
        original.record_event(event())
    with EvidenceRecorder.recover(path) as recovered:
        recovered.record_event(event())  # already delivered
        recovered.record_event(event(2, 10, "COMPLETE"))
        cost = ExecutedCost("cost", "journal-fixture", "human_1", "human", "e2",
                            "movement", 0, 10, CostEstimate(10, 2, 1))
        recovered.record_cost(cost)
        recovered.record_cost(cost)
    with EvidenceRecorder.recover(path) as recovered:
        result = recovered.export(tmp_path / "run", metadata()).to_dict()
        assert result["metrics"]["energy_est_wh"] == {"human_1": 2}
    assert len(path.read_bytes().splitlines()) == 5  # identity, 2 events, cost, seal


def test_deduplication_and_rejected_inputs_never_append(tmp_path):
    path = tmp_path / "journal.jsonl"
    with recorder(path) as value:
        value.record_event(event())
        before = active_bytes(value)
        value.record_event(event())
        with pytest.raises(ValueError, match="Conflicting"):
            value.record_event(replace(event(), detail="conflict"))
        with pytest.raises(ValueError, match="sequence"):
            value.record_event(event(3, 10))
        assert active_bytes(value) == before
        value.record_event(event(2, 10, "COMPLETE"))
        step = TraversalRecord("step", "journal-fixture", "human_1", 1, "route", "e2", 5, None)
        value.record_traversal(step)
        before = active_bytes(value)
        value.record_traversal(step)
        with pytest.raises(ValueError, match="Conflicting"):
            value.record_traversal(replace(step, distance_m=6))
        assert active_bytes(value) == before


@pytest.mark.parametrize("damage", ["truncate", "bad_json", "hash", "sequence", "identity", "nan"])
def test_corrupt_recovery_does_not_modify_source(tmp_path, damage):
    path = tmp_path / "journal.jsonl"
    with recorder(path) as value:
        value.record_event(event())
    raw = path.read_bytes()
    if damage == "truncate":
        raw = raw[:-1]
    elif damage == "bad_json":
        raw += b"{broken}\n"
    else:
        entries = [json.loads(x) for x in raw.splitlines()]
        if damage == "hash":
            entries[1]["payload"]["detail"] = "changed"
        elif damage == "sequence":
            entries[1]["seq"] = 2
        elif damage == "identity":
            entries[1]["payload"]["run_id"] = "another-run"
            entries = rehash(entries)
        else:
            raw += b'{"bad":NaN}\n'
        if damage != "nan":
            raw = b"".join((_canonical(x) + "\n").encode() for x in entries)
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        EvidenceRecorder.recover(path)
    assert path.read_bytes() == raw


def rehash(entries):
    previous = "0" * 64
    for seq, entry in enumerate(entries):
        entry["seq"], entry["previous_sha256"] = seq, previous
        body = {key: value for key, value in entry.items() if key != "sha256"}
        previous = hashlib.sha256(_canonical(body).encode()).hexdigest()
        entry["sha256"] = previous
    return entries


def test_valid_hashes_cannot_hide_semantically_duplicate_inputs(tmp_path):
    path = tmp_path / "journal.jsonl"
    with recorder(path) as value:
        value.record_event(event())
    entries = [json.loads(x) for x in path.read_bytes().splitlines()]
    entries.append(dict(entries[1]))
    raw = b"".join((_canonical(x) + "\n").encode() for x in rehash(entries))
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="Duplicate"):
        EvidenceRecorder.recover(path)
    assert path.read_bytes() == raw


def test_writer_is_exclusive_and_constructor_never_overwrites(tmp_path):
    path = tmp_path / "journal.jsonl"
    with recorder(path) as value:
        before = active_bytes(value)
        with pytest.raises(FileExistsError):
            recorder(path)
        with pytest.raises(OSError):
            EvidenceRecorder.recover(path)
        assert active_bytes(value) == before
    with EvidenceRecorder.recover(path):
        pass


def test_fsync_failure_does_not_mutate_memory_and_requires_recovery(tmp_path, monkeypatch):
    path = tmp_path / "journal.jsonl"
    with recorder(path) as value:
        def failed(_descriptor):
            raise OSError("synthetic fsync failure")
        with monkeypatch.context() as patch:
            patch.setattr("mge_mission.recorder.os.fsync", failed)
            with pytest.raises(OSError, match="synthetic fsync"):
                value.record_event(event())
        assert value._events == {}
        assert all(x is None for x in value._predicates.values())
        with pytest.raises(ValueError, match="journal failed"):
            value.record_event(event())
    # The failed acknowledgement may have written a complete line. Recovery
    # validates retained bytes; it does not claim the failed call was acknowledged.
    with EvidenceRecorder.recover(path) as recovered:
        assert list(recovered._events) == ["e1"]


def test_failed_evidence_commit_preserves_existing_memory(tmp_path, monkeypatch):
    path = tmp_path / "journal.jsonl"
    with recorder(path) as value:
        value.record_event(event())
        value.record_event(event(2, 10, "COMPLETE"))
        def failed(_descriptor):
            raise OSError("synthetic fsync failure")
        monkeypatch.setattr("mge_mission.recorder.os.fsync", failed)
        with pytest.raises(OSError):
            value.record_predicates(MissionEvidence("pred", "journal-fixture", 1,
                                                    "route", 10, True, True, True, True), "e2")
        assert value._records == {}
        assert all(x is None for x in value._predicates.values())


def test_partial_write_poisoning_and_truncated_recovery(tmp_path):
    path = tmp_path / "journal.jsonl"
    value = recorder(path)
    original = value._journal_stream

    class ShortWrite:
        def __getattr__(self, name):
            return getattr(original, name)

        def write(self, raw):
            return original.write(raw[:len(raw) // 2])

    value._journal_stream = ShortWrite()
    with pytest.raises(OSError, match="Incomplete journal write"):
        value.record_event(event())
    assert value._events == {}
    with pytest.raises(ValueError, match="journal failed"):
        value.record_event(event())
    value.close()
    before = path.read_bytes()
    with pytest.raises(ValueError, match="truncated"):
        EvidenceRecorder.recover(path)
    assert path.read_bytes() == before


def test_recovered_unknowns_cannot_be_relabelled_as_success(tmp_path):
    path = tmp_path / "journal.jsonl"
    with recorder(path) as value:
        populate(value, known=False)
    with EvidenceRecorder.recover(path) as recovered:
        with pytest.raises(ValueError, match="verified executed"):
            recovered.export(tmp_path / "run", metadata("SUCCESS"))
    assert not (tmp_path / "run").exists()


def test_discovery_and_task_completion_round_trip_through_typed_recovery(tmp_path):
    path = tmp_path / "journal.jsonl"
    with recorder(path) as original:
        original.record_event(replace(event(), event_type="TASK_DISCOVERED", task_id="poi", causality_id="obs"))
        original.record_discovery(ObservedTask("poi", "journal-fixture", 1, "obs", "human_1", "inspect",
                                               Point(0, 0), 10), "e1")
        original.record_event(replace(event(2, 10), event_type="TASK_STATE_CHANGED", task_id="poi",
                                      new_state="DONE", causality_id="work"))
        original.record_task_completion(TaskEvidence("work", "journal-fixture", 1,
                                                    "route", "poi", 10), "e2")
    with EvidenceRecorder.recover(path) as recovered:
        compare_evidence(original, recovered)


def test_seal_and_hashed_journal_survive_recovery_and_audit(tmp_path):
    context = {key: "a" * 64 if key.endswith("_sha256") else "fixture" for key in CONTEXT_FIELDS}
    context.update(model_id="fixture-model", profile_status="proposed")
    plan = FrozenBenchmarkPlan.from_dict(dict(
        schema_version="1.0.0", status="frozen", benchmark_id="fixture",
        frozen_at_utc="2026-11-14T07:00:00Z", hypotheses=["software fixture"],
        planned_seeds=[7], policies=["A", "B", "C"], experiment_kind="nominal", context=context,
        source_revision="b" * 40, source_manifest_sha256="c" * 64,
        metric_definitions={key: "fixture" for key in METRICS}))
    path = tmp_path / "journal.jsonl"
    with recorder(path, kind="SIMULATED_MISSION") as value:
        populate(value)
    with EvidenceRecorder.recover(path) as value:
        data = metadata("SUCCESS")
        data["freeze_sha256"] = plan.freeze_sha256
        outcome = value.export(tmp_path / "run", data)
        assert EvidenceAudit().audit(plan, outcome, tmp_path / "run") == ()
        assert outcome.to_dict()["recovered_from_journal"] is True
    copied = tmp_path / "run/recorder_journal.jsonl"
    assert copied.read_bytes() == path.read_bytes()
    item = next(x for x in outcome.to_dict()["artifacts"] if x["path"] == copied.name)
    assert item["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    with EvidenceRecorder.recover(path) as sealed:
        with pytest.raises(ValueError, match="sealed"):
            sealed.record_event(event(3, 11))
        with pytest.raises(ValueError, match="sealed"):
            sealed.export(tmp_path / "second-run", data)


def test_export_io_failure_after_seal_cannot_publish_a_second_outcome(tmp_path, monkeypatch):
    path = tmp_path / "journal.jsonl"
    with recorder(path) as value:
        populate(value, known=False)
        original_open = Path.open
        def failed_open(self, *args, **kwargs):
            if self.name == "recorder_journal.jsonl":
                raise OSError("synthetic export failure")
            return original_open(self, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", failed_open)
            with pytest.raises(OSError, match="export failure"):
                value.export(tmp_path / "partial", metadata())
        assert not (tmp_path / "partial/outcome.json").exists()
        with pytest.raises(ValueError, match="sealed"):
            value.export(tmp_path / "retry", metadata())
    with EvidenceRecorder.recover(path) as recovered:
        with pytest.raises(ValueError, match="sealed"):
            recovered.export(tmp_path / "retry", metadata())


def test_journal_paths_cannot_enter_reference_boundary(tmp_path):
    with pytest.raises(ValueError, match="reference"):
        recorder(tmp_path / "reference/journal.jsonl")
    assert not (tmp_path / "reference").exists()
