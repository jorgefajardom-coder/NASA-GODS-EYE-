"""Audit externally recorded A/B/C outcomes; never execute or fabricate missions."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/mge_mission"))

from mge_mission.audit import EvidenceAudit
from mge_mission.benchmark import FrozenBenchmarkPlan, RunOutcome, ScientificBenchmark


def read_json(path):
    def invalid_constant(_):
        raise ValueError("nonfinite JSON is not evidence")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=invalid_constant)


def analyze(plan_path, outcome_paths):
    report = {"schema_version": "1.0.0", "kind": "BENCHMARK_EVIDENCE_AUDIT",
              "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "scientific_approval": False, "integrated_mission_executed_by_tool": False,
              "input_errors": []}
    try:
        data = read_json(plan_path)
        if not isinstance(data, dict) or data.get("status") != "frozen":
            report.update(status="NOT_READY", reason_code="PLAN_NOT_FROZEN", observed_runs=0)
            return report, 2
        plan = FrozenBenchmarkPlan.from_dict(data)
    except (OSError, ValueError) as exc:
        report.update(status="NOT_READY", reason_code="PLAN_INVALID", detail=str(exc), observed_runs=0)
        return report, 2
    report["plan_file_sha256"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    benchmark, auditor = ScientificBenchmark(plan), EvidenceAudit()
    for path in outcome_paths:
        try:
            outcome = RunOutcome.from_dict(read_json(path))
            benchmark.add(outcome, findings=auditor.audit(plan, outcome, path.parent))
        except (OSError, ValueError, TypeError) as exc:
            report["input_errors"].append({"path": str(path), "code": "OUTCOME_INVALID", "detail": str(exc)})
    report.update(benchmark.summary())
    report["status"] = "AUDITED" if outcome_paths else "NO_EXECUTIONS"
    has_errors = bool(report["input_errors"] or report.get("diagnostics"))
    has_errors |= any(item.get("severity") == "error"
                      for row in report["retained_rows"] for item in row["findings"])
    return report, 1 if has_errors else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--outcome", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    if args.output_dir and (args.output_dir / "benchmark_audit.json").exists():
        parser.error("existing audit records are immutable; choose another output directory")
    report, code = analyze(args.plan.resolve(), [path.resolve() for path in args.outcome])
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        target = args.output_dir / "benchmark_audit.json"
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
        print(json.dumps({"status": report["status"], "scientific_approval": False, "report": str(target)}))
    else:
        print(json.dumps(report, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
