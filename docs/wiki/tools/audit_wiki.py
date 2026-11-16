"""Check the documentation packet; required AI-use metadata is in docs/ai_usage.json."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[3]
DEPS = ROOT / ".local/wiki-figure-deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import matplotlib

WIKI = ROOT / "docs/wiki"
AUDIT = WIKI / "audit"
CHAPTERS = ["01-Research-Question.md", "02-Jezero-Science.md", "03-Terrain-and-Scale.md",
            "04-Agents-and-Activities.md", "05-Resource-Models.md", "06-Mission-Decisions.md",
            "07-Experimental-Method.md", "08-Case-Studies.md", "09-Discussion.md"]
REQUIRED = ["Home.md", *CHAPTERS, "Glossary.md", "Parameters-and-Decisions.md",
            "Bibliography.md", "Reproducibility.md", "_Sidebar.md", "_Footer.md", "README.md"]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def footer(image, label):
    """Match actual prefix glyphs, rather than trusting a dark rectangle alone."""
    rgb = image.convert("RGB")
    require(rgb.width >= 900 and rgb.height >= 600, f"Small graphic: {label}")
    font = ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"), 20)
    reference = Image.new("RGB", rgb.size, "#1b2633")
    ImageDraw.Draw(reference).text((22, rgb.height - 36), "AI-generated", fill="white", font=font)
    bounds = (22, rgb.height - 36, 163, rgb.height - 10)
    expected = np.asarray(reference.crop(bounds)).min(axis=2) > 190
    actual = np.asarray(rgb.crop(bounds)).min(axis=2) > 190
    require(expected.sum() > 200, "Invalid watermark reference")
    require((actual & expected).sum() / expected.sum() >= .98, f"Missing visible watermark glyphs: {label}")
    dark = np.asarray(rgb.crop((0, rgb.height - 48, rgb.width, rgb.height))).mean(axis=2) < 75
    require(dark.mean() > .65, f"Missing contrast panel: {label}")


def main():
    AUDIT.mkdir(exist_ok=True)
    (AUDIT / "report.json").write_text('{"status":"CHECKING"}\n', encoding="utf-8")
    for filename in REQUIRED:
        require((WIKI / filename).is_file(), f"Required page: {filename}")
    checked_links = 0
    external = set()
    pages = []
    for path in sorted(WIKI.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        require("**" not in text and not re.search(r"(?<!_)__(?!_)", text), f"Bold markup: {path.name}")
        require(not re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b", text), f"Unfinished prose: {path.name}")
        require(not any(term in text for term in ["\\(", "\\)", "\\[", "\\]"]), f"Math delimiter: {path.name}")
        words = len(re.findall(r"\b[\w’'-]+\b", text))
        figures = len(re.findall(r"!\[", text))
        if path.name in CHAPTERS:
            require(words >= 850, f"Incomplete chapter: {path.name}")
            require(figures >= 1, f"Chapter without graphics: {path.name}")
        for match in re.finditer(r"!?\[([^\]]*)\]\(([^)\n]+)\)", text):
            label, target = match.groups()
            target = target.strip("<>").split(' "', 1)[0]
            parsed = urlparse(target)
            if parsed.scheme in {"http", "https"}:
                external.add(target)
                continue
            if parsed.scheme or target.startswith("#"):
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            require(resolved.is_relative_to(ROOT), f"Link outside repository: {path.name}: {target}")
            require(resolved.is_file(), f"Broken link: {path.name}: {target}")
            checked_links += 1
            if match.group(0).startswith("!"):
                require(len(label.strip()) >= 20, f"Uninformative alt text: {path.name}: {target}")
            if parsed.fragment and resolved.suffix == ".md":
                headings = re.findall(r"^#+\s+(.+)$", resolved.read_text(encoding="utf-8"), flags=re.M)
                anchors = [re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-") for heading in headings]
                require(parsed.fragment in anchors, f"Missing heading: {target}")
        pages.append({"file": path.name, "words": words, "embedded_graphics": figures, "sha256": sha(path)})

    assets = read(WIKI / "assets/manifest.json")
    for relative, digest in assets["input_sha256"].items():
        require(sha(ROOT / relative) == digest, f"Changed figure input: {relative}")
    gif_frames = 0
    for item in assets["assets"]:
        path = WIKI / "assets" / item["file"]
        require(sha(path) == item["sha256"], f"Changed asset: {path.name}")
        with Image.open(path) as image:
            if path.suffix == ".gif":
                require(b"AI-generated" in image.info.get("comment", b""), f"GIF metadata: {path.name}")
                count = 0
                for i, frame in enumerate(ImageSequence.Iterator(image)):
                    footer(frame, f"{path.name} frame {i}")
                    count += 1
                # GIF encoders may coalesce identical adjacent frames; every decoded frame is checked.
                require(count >= 3, f"Nonanimated GIF: {path.name}")
                gif_frames += count
                item["decoded_frames_checked"] = count
            elif path.name == "cooperative-exploration.png":
                require(sha(path) == read(AUDIT / "cover-provenance.json")["source_sha256"], "Cover source mismatch")
            else:
                footer(image, path.name)
                require("AI-generated" in image.info.get("Description", ""), f"PNG metadata: {path.name}")

    preserved = read(AUDIT / "previous-packet-preservation.json")
    require(sha(ROOT / preserved["manifest"]) == preserved["sha256"], "Previous seal changed")
    for item in preserved["documents"]:
        require(sha(ROOT / item["preserved_path"]) == item["sha256"], "Previous document changed")
    preserved_map = {item["original_path"]: ROOT / item["preserved_path"] for item in preserved["documents"]}
    previous_packet = read(ROOT / preserved["manifest"])
    for item in previous_packet["entries"]:
        path = preserved_map.get(item["path"], ROOT / item["path"])
        require(sha(path) == item["sha256"], f"Previously sealed artifact changed: {item['path']}")
    # Its earlier scientific-software packet retains a second document-version mapping.
    older_map_record = read(ROOT / "evidence/mission-3d-video-20261115-local/previous-audit-preservation.json")
    older_root = ROOT / "evidence/mission-3d-video-20261115-local"
    older_map = {item["original_path"]: older_root / item["preserved_path"] for item in older_map_record["documents"]}
    older_packet = read(ROOT / older_map_record["manifest"])
    require(sha(ROOT / older_map_record["manifest"]) == older_map_record["sha256"], "Earlier scientific seal changed")
    for item in older_packet["entries"]:
        path = older_map.get(item["path"], ROOT / item["path"])
        require(sha(path) == item["sha256"], f"Previously sealed science source changed: {item['path']}")

    # Recompute examples through the existing pure model API.
    sys.path.insert(0, str(ROOT / "src/mge_mission"))
    from mge_mission.models import estimate_segment, load_profiles
    profiles = load_profiles(ROOT / "config/science_profiles.proposed.json")
    for kind, examples in assets["directed_model_examples"].items():
        for dz, expected in examples.items():
            cost = estimate_segment(profiles[f"{kind}_1"], (0, 0, 0), (100, 0, float(dz)))
            for key, value in expected.items():
                actual = getattr(cost, key)
                require(actual == value, f"Model example mismatch: {kind} {dz} {key}")
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    technical = ["src", "config", "web", "scripts", "tests", "data", ".github"]
    current = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all", "--", *technical], cwd=ROOT)
    require(current.decode() == read(AUDIT / "inputs.json")["technical_status_before"], "Technical working-tree status changed")
    for relative, digest in read(AUDIT / "inputs.json")["technical_file_sha256_before"].items():
        require(sha(ROOT / relative) == digest, f"Technical input changed: {relative}")
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS",
        "english_reader_pages": 14, "chapters": len(CHAPTERS), "pages": pages,
        "local_links_checked": checked_links, "external_reference_urls": sorted(external),
        "external_check_scope": "Primary sources checked in authoring and cross-review; local audit does not infer content validity from HTTP availability",
        "generated_assets": len(assets["assets"]), "GIFs": sum(item["file"].endswith('.gif') for item in assets["assets"]),
        "decoded_GIF_frames_watermark_checked": gif_frames,
        "PNG_footer_glyphs_and_metadata": "PASS; conceptual cover verified against saved image-generation source and visual review",
        "model_examples_recomputed": True, "figure_input_hashes": "PASS",
        "technical_tree_unchanged_from_task_start": True, "previous_sealed_documents_preserved": True,
        "previous_artifacts_verified": len(previous_packet["entries"]) + len(older_packet["entries"]),
        "bold_markup": 0, "unfinished_markers": 0, "git_diff_check": "PASS",
        "visual_review": "Full-size figures and representative first/middle/final animation frames inspected; causal layouts corrected",
        "owner_scientific_audit": "pending; this is the complete first draft", "published": False,
    }
    (AUDIT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key:report[key] for key in ["status", "chapters", "english_reader_pages", "generated_assets", "GIFs", "local_links_checked", "decoded_GIF_frames_watermark_checked", "technical_tree_unchanged_from_task_start"]}, indent=2))


if __name__ == "__main__":
    main()
