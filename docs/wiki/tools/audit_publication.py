"""Audit the bounded scientific-Wiki publication; AI-use metadata: docs/ai_usage.json.

Standard library only. Reads the package and its frozen base; writes nothing.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[3]
WIKI = ROOT / "docs/wiki"
MANIFEST = WIKI / "audit/publication-manifest.json"
CHAPTERS = ["01-Research-Question.md", "02-Jezero-Science.md", "03-Terrain-and-Scale.md",
            "04-Agents-and-Activities.md", "05-Resource-Models.md", "06-Mission-Decisions.md",
            "07-Experimental-Method.md", "08-Case-Studies.md", "09-Discussion.md"]
READERS = ["Home.md", *CHAPTERS, "Glossary.md", "Parameters-and-Decisions.md", "Bibliography.md", "Reproducibility.md"]

def require(ok, message):
    if not ok:
        raise AssertionError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    base = manifest["baseline_main_sha"]
    files = {item["path"]: item for item in manifest["entries"]}
    for name, item in files.items():
        require(not name.startswith(("src/", "config/", "scripts/", "tests/", "web/", "data/", ".github/")), f"Technical payload: {name}")
        require(name.startswith(("docs/", "evidence/")), f"Unsupported payload: {name}")
        require(not any(part in {".browser-profile", "__pycache__", "frames", "private", "reference", "evaluator"} for part in Path(name).parts), f"Excluded payload: {name}")
        path = ROOT / name
        require(path.is_file(), f"Missing exported file: {name}")
        require(path.stat().st_size == item["size_bytes"], f"Size mismatch: {name}")
        require(digest(path.read_bytes()) == item["sha256"], f"Hash mismatch: {name}")
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")
              if path.is_file() and "__pycache__" not in path.parts
              and ".git" not in path.parts and path != MANIFEST}
    # A full checkout additionally contains base files; an overlay contains exactly the manifest entries.
    extras = sorted(actual - files.keys())
    for name in extras:
        existing = subprocess.run(["git", "cat-file", "-e", f"{base}:{name}"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        require(existing.returncode == 0, f"Unmanifested non-base file: {name}")
    for page in READERS:
        require((WIKI / page).is_file(), f"Missing reader page: {page}")
    historical = WIKI / "audit/local-draft-manifest.json"
    require(digest(historical.read_bytes()) == manifest["historical_draft_manifest_sha256"], "Historical draft seal changed")
    draft = json.loads(historical.read_text(encoding="utf-8"))
    source_entries = {item["path"]: item["sha256"] for item in draft["entries"]}
    for name, expected in manifest["sealed_asset_sha256"].items():
        require(source_entries[f"docs/wiki/assets/{name}"] == expected, f"Unsealed asset provenance: {name}")
        require(digest((WIKI / "assets" / name).read_bytes()) == expected, f"Changed watermarked asset: {name}")
    require(len(manifest["sealed_asset_sha256"]) == 21, "Asset count")
    require(sum(name.endswith(".gif") for name in manifest["sealed_asset_sha256"]) == 3, "GIF count")

    fallbacks = set()
    cache = {}
    def content(relative):
        path = ROOT / relative
        if path.is_file():
            return path.read_bytes()
        if relative not in cache:
            result = subprocess.run(["git", "show", f"{base}:{relative}"], cwd=ROOT, capture_output=True)
            require(result.returncode == 0, f"Missing local/base link target: {relative}")
            cache[relative] = result.stdout
        fallbacks.add(relative)
        return cache[relative]

    links = 0
    external = set()
    for path in sorted(WIKI.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        require("**" not in text, f"Bold formatting: {path.name}")
        require(not re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b", text), f"Unfinished page: {path.name}")
        if path.name in CHAPTERS:
            require(len(re.findall(r"\b[\w’'-]+\b", text)) >= 850, f"Short chapter: {path.name}")
            require("![" in text, f"Chapter without graphics: {path.name}")
        for label, target in re.findall(r"!?\[([^\]]*)\]\(([^)\n]+)\)", text):
            target = target.strip("<>").split(' "', 1)[0]
            parsed = urlparse(target)
            if parsed.scheme in {"http", "https"}:
                external.add(target)
                continue
            if parsed.scheme or not parsed.path:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            require(resolved.is_relative_to(ROOT), f"Link outside repository: {target}")
            relative = resolved.relative_to(ROOT).as_posix()
            body = content(relative)
            if parsed.fragment and resolved.suffix == ".md":
                headings = re.findall(r"^#+\s+(.+)$", body.decode("utf-8"), re.M)
                anchors = [re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-") for heading in headings]
                require(parsed.fragment in anchors, f"Missing heading: {target}")
            links += 1
    raw = json.loads(content("evidence/mission-cost-experiment-20261115-local-v2/experiment.json"))
    require(raw["run_id"] == "local-cost-eva-bunsen-20261115-02", "Wrong case identity")
    require(raw["world_provenance"]["full_world_exposed"] is False, "Private world disclosed")
    original = json.loads((WIKI / "audit/report.json").read_text())
    require(original["status"] == "PASS" and original["decoded_GIF_frames_watermark_checked"] == 57, "Historical watermark record")
    print(json.dumps({
        "checked_at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS",
        "classification": "BOUNDED_SCIENTIFIC_WIKI_PUBLICATION_CHECK",
        "reader_pages": len(READERS), "chapters": len(CHAPTERS), "assets": 21, "GIFs": 3,
        "all_assets_identical_to_watermark_checked_draft": True,
        "watermark_check_scope": "Byte-identical to the sealed draft whose 57 decoded GIF frames and PNGs were checked; this standard-library check verifies hashes rather than decoding media again",
        "payload_files_checked": len(files), "local_links_checked": links,
        "frozen_base_link_fallbacks": sorted(fallbacks), "external_reference_urls": sorted(external),
        "technical_payload_files": 0, "scientific_owner_audit": "pending",
        "historical_draft_and_local_archive_status": "Preserved as historical records; full local3394-artifact archive is not part of the bounded publication",
        "published": False,
    }, indent=2))

if __name__ == "__main__":
    main()
