"""Frozen design, source identity and durable append-only pilot records."""
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile

import numpy as np

REGIONS = (
    {"id": "bright", "candidate_id": "JZ-ROI-01", "name": "Bright Angel–Neretva", "lat": 18.496798465, "lon": 77.3045133, "campaign": "CAM-BRIGHT"},
    {"id": "hawksbill", "candidate_id": "JZ-ROI-02", "name": "Hawksbill–Hogwallow", "lat": 18.45835024, "lon": 77.40732773, "campaign": "CAM-HAWKSBILL"},
    {"id": "bunsen", "candidate_id": "JZ-ROI-04", "name": "Bunsen Peak", "lat": 18.491816235, "lon": 77.32719163, "campaign": "CAM-BUNSEN"},
)
FAMILIES = ("unchanged", "detour", "blocked", "relief", "resource")


def now():
    return datetime.now(timezone.utc)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def array_hash(array):
    a = np.asarray(array, dtype="<f8").copy()
    a[np.isnan(a)] = np.nan
    return hashlib.sha256(a.tobytes(order="C")).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


class Journal:
    """Replay refuses corrupt/truncated/conflicting records without changing them."""
    def __init__(self, path, identity, retain_payload=True):
        self.path, self.identity = Path(path), identity
        self.retain_payload, self.failed = retain_payload, False
        self.rows = []
        self.ids = {}
        if self.path.exists():
            raw = self.path.read_bytes()
            if raw and not raw.endswith(b"\n"):
                raise ValueError("Truncated journal; original retained")
            for line in raw.splitlines():
                item = json.loads(line)
                if item["seq"] != len(self.rows)+1 or item["identity"] != identity:
                    raise ValueError("Journal sequence/identity conflict")
                if item["case_id"] in self.ids or item["payload_sha256"] != digest(item["payload"]):
                    raise ValueError("Journal duplicate/hash conflict")
                if not self.retain_payload:
                    item={k:v for k,v in item.items() if k!="payload"}
                self.rows.append(item)
                self.ids[item["case_id"]] = item

    def append(self, case_id, payload):
        if self.failed:
            raise RuntimeError("Journal write failed; reopen and validate before reuse")
        if case_id in self.ids:
            if self.ids[case_id]["payload_sha256"] != digest(payload):
                raise ValueError("Conflicting duplicate case")
            return False
        item = {"seq": len(self.rows)+1, "identity": self.identity, "case_id": case_id,
                "recorded_at_utc": now().isoformat(), "payload_sha256": digest(payload), "payload": payload}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open("ab") as stream:
                stream.write((canonical(item)+"\n").encode())
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            self.failed=True
            raise
        if not self.retain_payload:
            item={k:v for k,v in item.items() if k!="payload"}
        self.rows.append(item)
        self.ids[case_id] = item
        return True


def initialize(args, repo, source):
    root = args.root.resolve()
    if root.exists():
        raise FileExistsError("Research identity already exists; use existing protocol")
    if not 1 <= args.budget_s <= 28800:
        raise ValueError("Budget must be between one second and eight hours")
    starts = datetime.fromisoformat(args.started_at)
    if starts.tzinfo is None:
        raise ValueError("Start must include timezone")
    source.mkdir(parents=True, exist_ok=True)
    paths = ["src/mge_mission", "src/mge_planning", "src/mge_mapping", "src/mge_data", "scripts", "config", "data/sample", "data/dataset.schema.json", "data/manifest.schema.json"]
    archive = subprocess.check_output(["git", "archive", args.source_sha, *paths], cwd=repo)
    expected_files=[]
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        for entry in bundle:
            dest = (source / entry.name).resolve()
            if not dest.is_relative_to(source.resolve()) or entry.issym() or entry.islnk():
                raise ValueError("Unsafe source archive")
            if entry.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            elif entry.isfile():
                dest.parent.mkdir(parents=True, exist_ok=True)
                content=bundle.extractfile(entry).read()
                if dest.exists():
                    if dest.read_bytes()!=content: raise ValueError("Existing frozen source differs from requested commit")
                else:
                    dest.write_bytes(content)
                expected_files.append(dest)
    lock = {p.relative_to(source).as_posix(): sha(p) for p in sorted(expected_files)}
    write_new(root / "source-lock.json", {"published_sha": args.source_sha, "source_sha256": lock,
              "local_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip(),
              "archive_sha256": hashlib.sha256(archive).hexdigest()})
    config = {"schema_version": "1.0.0", "study_id": root.name, "classification": "LOCAL_EXPLORATORY_SIMULATED_NOT_OPERATIONAL",
              "started_at_utc": starts.isoformat(), "deadline_utc": (starts+timedelta(seconds=args.budget_s)).isoformat(),
              "new_work_cutoff_utc": (starts+timedelta(seconds=max(0,args.budget_s-1800))).isoformat(), "budget_s": args.budget_s,
              "source_sha": args.source_sha, "source_lock_sha256": sha(root / "source-lock.json"),
              "root_seed": 20261115, "regions": REGIONS, "families": FAMILIES,
              "sizes_m": [128,256,512,1024], "optional_scale_m": 2048, "resolution_m": 4, "native_resolution_m": 20,
              "seeds_per_family": 16, "exploration_seed_indices": list(range(12)), "holdout_seed_indices": list(range(12,16)),
              "modes": ["FAST","SAFE"], "policies": ["none","corridor","alternatives"], "agents": ["human_1","rover_1"],
              "search_limits": {"timeout_s": 2.0,"max_labels": 200000}, "max_compute_processes": 2,
              "download_limit_bytes": 2*1024**3, "storage_limit_bytes": 10*1024**3,
              "research_max_sigma_m": 3.0, "strict_max_sigma_m": 1.0, "prior_sigma_m": 2.5,
              "budget_factor": [.8,1.2], "reserve_fractions": [.1,.2,.3], "wait_factor": [.5,1.5],
              "sample_workflow_s": [600,900], "rover_inspection_s": [300,600,900],
              "relief_amplitude_m": [.1,.2,.3], "correlation_length_m": [8,16,32], "obstacle_cells": [1,2,4],
              "footprint_radius_m": [4,8,12], "block_mean_tolerance_m": .001,
              "endpoint_tries": 64, "endpoint_separation_side_fraction": [.125,.5],
              "numerical_agreement": {"relative": 1e-5, "absolute": .001},
              "scope_authorization": "Owner explicitly requests local overnight assessment; D-DEL-03 delivery and science gates unchanged",
              "scientific_approval": False, "cost_agreement": False, "mission_execution_authorized": False,
              "baseline_input": False, "rendering": False, "new_mock": False,
              "versions": {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform()}}
    write_new(root / "protocol.json", config)
    from shutil import copyfile
    for name, dest in [("config/science_profiles.proposed.json","profiles.source.json"),
                       ("config/mission_jezero.experimental.yaml","control.source.yaml")]:
        copyfile(source / name, root / dest)
    for name in ("assumptions.proposed.json", "campaign_analysis.json", "sources.json"):
        copyfile(repo / "evidence/agent-campaign-proposal-20261114" / name, root / ("campaign-"+name))
    print(canonical({"initialized": str(root), "deadline": config["deadline_utc"], "published_sha": args.source_sha}), flush=True)


def check_identity(root, source):
    cfg = read(root / "protocol.json")
    lock = read(root / "source-lock.json")
    if sha(root / "source-lock.json") != cfg["source_lock_sha256"]:
        raise ValueError("Source lock changed")
    for name, expected in lock["source_sha256"].items():
        if sha(source / name) != expected:
            raise ValueError("Pinned upstream source changed: "+name)
    return cfg


def cutoff(cfg):
    return now() >= datetime.fromisoformat(cfg["new_work_cutoff_utc"])


def storage_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob("*") if p.is_file())


def peak_memory_bytes():
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                      *[(name,ctypes.c_size_t) for name in ("PeakWorkingSetSize","WorkingSetSize","QuotaPeakPagedPoolUsage","QuotaPagedPoolUsage","QuotaPeakNonPagedPoolUsage","QuotaNonPagedPoolUsage","PagefileUsage","PeakPagefileUsage")]]
        counters=Counters(); counters.cb=ctypes.sizeof(counters)
        process=ctypes.windll.kernel32.GetCurrentProcess
        process.restype=wintypes.HANDLE
        get_memory=ctypes.windll.psapi.GetProcessMemoryInfo
        get_memory.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        get_memory.restype=wintypes.BOOL
        if get_memory(process(),ctypes.byref(counters),counters.cb):
            return int(counters.PeakWorkingSetSize)
        return None
    import resource
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
