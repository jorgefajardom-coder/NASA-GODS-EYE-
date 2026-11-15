"""Compare a published planner snapshot with mission science costs on synthetic grids."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/mge_mission"))

from mge_mission.conformance import run_conformance
from mge_mission.models import load_profiles


def snapshot_from_ref(reference, folder):
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", reference) or reference.startswith("-"):
        raise ValueError("supply a local branch, tag or full commit reference")
    revision = subprocess.check_output(["git", "rev-parse", "--verify", reference + "^{commit}"],
                                       cwd=ROOT, text=True).strip()
    archive_path = folder / "planner.tar"
    subprocess.run(["git", "archive", "--format=tar", "--output=" + str(archive_path),
                    revision, "src/mge_planning"], cwd=ROOT, check=True, capture_output=True)
    source = folder / "source"
    source.mkdir()
    with tarfile.open(archive_path) as archive:
        archive.extractall(source, filter="data")
    files = {path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(source.rglob("*")) if path.is_file()}
    package = "src/mge_planning/mge_planning"
    manifest = {"schema_version": "1.0.0",
                "repository": "https://github.com/jorgefajardom-coder/NASA-GODS-EYE-.git",
                "revision": revision, "package_root": package, "files": files}
    (source / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                               encoding="utf-8", newline="\n")
    return source / package, revision


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--planner-ref")
    choice.add_argument("--planner-package", type=Path)
    parser.add_argument("--planner-revision")
    parser.add_argument("--backend", choices=("scientific", "legacy"), default="scientific",
                        help="Scientific production backend by default; legacy reproduces historical comparisons")
    parser.add_argument("--profiles", type=Path, default=ROOT / "config/science_profiles.proposed.json")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        parser.error("run-id must contain only letters, digits, hyphens and underscores")
    target = args.output_dir / "conformance.json"
    if target.exists():
        parser.error("existing conformance evidence is immutable; choose another output directory")
    profiles = load_profiles(args.profiles)
    if args.planner_package:
        if not args.planner_revision:
            parser.error("--planner-package requires an exact --planner-revision")
        report = run_conformance(args.planner_package, profiles, args.planner_revision, backend=args.backend)
    else:
        scratch = ROOT / "tmp"
        scratch.mkdir(exist_ok=True)
        if not scratch.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("temporary snapshot parent must remain within the workspace")
        with tempfile.TemporaryDirectory(prefix="planner-conformance-", dir=scratch) as folder:
            temporary = Path(folder).resolve()
            if not temporary.is_relative_to(scratch.resolve()):
                raise ValueError("temporary planner snapshot must remain within the workspace")
            package, revision = snapshot_from_ref(args.planner_ref, temporary)
            report = run_conformance(package, profiles, revision, backend=args.backend)
    report.update(run_id=args.run_id, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                  profile_registry_sha256=hashlib.sha256(args.profiles.read_bytes()).hexdigest(),
                  command=[sys.executable, *sys.argv])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "authorization": report["authorization"],
                      "summary": report.get("summary"), "report": str(target)}))
    # Disagreement is a valid diagnostic result, never route authorization.
    return 0 if report["status"] == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
