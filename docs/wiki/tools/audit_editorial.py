"""Read-only checks for a scientific-Wiki editorial edition.

Required AI-use metadata is recorded in docs/AI_USAGE.md and docs/ai_usage.json.
Checks use the standard library; Pillow adds media decoding and footer-presence
checks. Visible wording and scientific meaning require the recorded visual
review: this program does not perform OCR or establish owner approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[3]
WIKI = ROOT / "docs/wiki"
DEFAULT_MANIFEST = WIKI / "audit/editorial-20261115/manifest.json"
CHAPTERS = [
    "01-Research-Question.md", "02-Jezero-Science.md", "03-Terrain-and-Scale.md",
    "04-Agents-and-Activities.md", "05-Resource-Models.md", "06-Mission-Decisions.md",
    "07-Experimental-Method.md", "08-Case-Studies.md", "09-Discussion.md",
]
READERS = ["Home.md", *CHAPTERS, "Glossary.md", "Parameters-and-Decisions.md",
           "Bibliography.md", "Reproducibility.md"]
ACCEPTED_IDS = {1, 2, 3, 4, 5, 6, 7, 9, 10}
VETOED_RAW_IDS = {8, 12, 14, 15, 16, 17, 20}

# An isolated documentation environment may live above a prepared overlay.
for ancestor in (ROOT, *ROOT.parents):
    dependencies = ancestor / ".local/wiki-figure-deps"
    if dependencies.is_dir():
        sys.path.insert(0, str(dependencies))
        break
try:
    from PIL import Image
except ImportError:
    Image = None


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def heading_anchor(heading):
    heading = re.sub(r"[`*_]", "", heading.lower())
    return re.sub(r"[^\w\- ]", "", heading).replace(" ", "-")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST,
                        help="Edition manifest; defaults to the 2026-11-15 editorial edition")
    parser.add_argument("--require-pixels", action="store_true",
                        help="Fail if Pillow is unavailable instead of returning a partial static audit")
    args = parser.parse_args(argv)
    manifest = json_read(args.manifest)
    require(isinstance(manifest.get("schema"), str), "Missing edition schema")
    base = manifest["baseline_main_sha"]
    require(re.fullmatch(r"[0-9a-f]{40}", base) is not None, "Invalid main baseline SHA")
    require(re.fullmatch(r"[0-9a-f]{40}", manifest["baseline_native_wiki_sha"]) is not None,
            "Invalid native Wiki baseline SHA")
    require(manifest.get("owner_review_required") is True,
            "The edition must retain the package-required owner review gate")
    package = manifest["package"]
    require(package["images_count"] == 20, "Package image count")
    for key in ("zip_sha256", "manifest_sha256"):
        require(re.fullmatch(r"[0-9a-f]{64}", package[key]) is not None, f"Invalid package {key}")

    baseline_cache = {}
    fallback_links = set()

    def baseline(relative):
        if relative not in baseline_cache:
            result = subprocess.run(["git", "show", f"{base}:{relative}"], cwd=ROOT,
                                    capture_output=True)
            require(result.returncode == 0, f"Missing frozen-base file: {relative}")
            baseline_cache[relative] = result.stdout
        return baseline_cache[relative]

    def resolve_wiki(relative):
        path = (WIKI / relative).resolve()
        require(path.is_relative_to(WIKI.resolve()), f"Wiki path escapes its directory: {relative}")
        return path

    def repository_bytes(relative, *, allow_base=True):
        path = (ROOT / relative).resolve()
        require(path.is_relative_to(ROOT.resolve()), f"Repository path escapes root: {relative}")
        if path.is_file():
            return path.read_bytes()
        require(allow_base, f"Missing edition file: {relative}")
        fallback_links.add(relative)
        return baseline(relative)

    accepted = manifest["accepted"]
    excluded = manifest["excluded"]
    accepted_ids = [item["source_id"] for item in accepted]
    excluded_ids = [item["source_id"] for item in excluded]
    require(len(accepted_ids) == len(set(accepted_ids)) == 9, "Duplicate/missing accepted asset")
    require(set(accepted_ids) == ACCEPTED_IDS, "Accepted asset selection differs from reviewed scope")
    require(len(excluded_ids) == len(set(excluded_ids)) == 11, "Duplicate/missing excluded asset")
    require(set(excluded_ids) == set(range(1, 21)) - ACCEPTED_IDS,
            "Selection/exclusion must account for all 20 source assets")
    require(not (set(accepted_ids) & VETOED_RAW_IDS), "Vetoed raw image accepted")
    require(all(isinstance(row.get("reason"), str) and row["reason"].strip() for row in excluded),
            "Every excluded asset needs a reason")

    protected = manifest["protected_paths_sha256"]
    require("docs/wiki/assets/manifest.json" in protected, "Original asset manifest is not protected")
    for relative, expected in protected.items():
        require(re.fullmatch(r"[0-9a-f]{64}", expected) is not None, f"Invalid protected digest: {relative}")
        require(digest(repository_bytes(relative)) == expected, f"Protected file changed: {relative}")
        require(digest(baseline(relative)) == expected, f"Protection differs from frozen baseline: {relative}")
    original_assets = json.loads(repository_bytes("docs/wiki/assets/manifest.json"))
    require(len(original_assets["assets"]) == 21, "Unexpected original asset registry")
    original_gifs = []
    for original in original_assets["assets"]:
        relative = "docs/wiki/assets/" + original["file"]
        require(relative in protected, f"Original asset omitted from protection: {relative}")
        require(digest(repository_bytes(relative)) == original["sha256"], f"Original asset changed: {relative}")
        if relative.endswith(".gif"):
            original_gifs.append(relative)
    require(len(original_gifs) == 3, "Original animation count")

    payload_names = []
    for item in manifest["payload_files"]:
        relative = item["path"]
        payload_names.append(relative)
        require(not any(part in {".git", ".local", ".browser-profile", "private", "reference", "evaluator", "frames"}
                        for part in Path(relative).parts), f"Excluded payload path: {relative}")
        numbered_image = re.match(r"^(\d{2})[_-]", Path(relative).name)
        if Path(relative).suffix.lower() in {".png", ".webp", ".jpg", ".jpeg", ".gif"} and numbered_image:
            require(int(numbered_image.group(1)) not in VETOED_RAW_IDS,
                    f"Vetoed raw source image in publication payload: {relative}")
        data = repository_bytes(relative, allow_base=False)
        require(digest(data) == item["sha256"], f"Edition payload hash mismatch: {relative}")
        if "size_bytes" in item:
            require(len(data) == item["size_bytes"], f"Edition payload size mismatch: {relative}")
        if not relative.startswith("docs/"):
            require(data == baseline(relative), f"Non-documentary file changed: {relative}")
    require(len(payload_names) == len(set(payload_names)), "Duplicate edition payload path")

    ai_registry = json.loads(repository_bytes("docs/ai_usage.json"))
    collection = "docs/wiki/assets/imagegen-20261115"
    declared_collection = any(
        any(path.rstrip("/") == collection or path.startswith(collection + "/")
            for path in use.get("paths", []) if isinstance(path, str))
        for use in ai_registry.get("uses", [])
    )
    require(declared_collection, "AI-use metadata must explicitly identify the new ImageGen collection")
    ai_description = repository_bytes("docs/AI_USAGE.md").decode("utf-8-sig")
    require("imagegen-20261115" in ai_description,
            "Descriptive AI-use declaration must identify the new ImageGen collection")

    expected_media = set()
    media_checks = []
    manual_text_records = []
    prompt_paths = []
    for item in accepted:
        identifier = item["source_id"]
        require(isinstance(item.get("slug"), str) and item["slug"], f"Missing slug: {identifier}")
        require("concept" in item["classification"].lower(), f"Unclassified illustration: {identifier}")
        visible = item["expected_visible_text"]
        require(isinstance(visible, list) and visible and all(isinstance(text, str) and text.strip() for text in visible),
                f"Missing manual text checklist: {identifier}")
        require(any("AI-generated" in text for text in visible), f"Missing expected AI watermark: {identifier}")
        prompt_path = resolve_wiki(item["prompt_path"])
        require(prompt_path.is_file(), f"Missing generation provenance: {item['prompt_path']}")
        prompt = json_read(prompt_path)
        tool = prompt.get("tool", prompt.get("generation_tool"))
        require(isinstance(tool, str) and tool.strip(), f"Missing AI tool provenance: {identifier}")
        prompt_text = prompt.get("prompt", prompt.get("prompt_text"))
        require(isinstance(prompt_text, str) and len(prompt_text.strip()) >= 30, f"Missing generation prompt: {identifier}")
        require(any(prompt.get(key) for key in ("source_asset", "source_id", "source_png_sha256", "source_provenance")),
                f"Missing source-image provenance: {identifier}")
        prompt_paths.append(item["prompt_path"])
        dimensions = item["dimensions_px"]
        require(len(dimensions) == 2 and all(isinstance(value, int) and value > 0 for value in dimensions),
                f"Invalid image dimensions: {identifier}")
        require(dimensions[0] >= 1200 and dimensions[1] >= 600, f"Small editorial image: {identifier}")
        for extension in ("png", "webp"):
            relative = item[extension + "_path"]
            require(relative.startswith("assets/imagegen-20261115/"), f"Image outside edition directory: {relative}")
            path = resolve_wiki(relative)
            require(path.suffix.lower() == "." + extension, f"Unexpected image extension: {relative}")
            require(path.is_file(), f"Missing editorial image: {relative}")
            require(digest(path.read_bytes()) == item[extension + "_sha256"], f"Image hash mismatch: {relative}")
            expected_media.add(path)
            check = {"path": relative, "sha256": item[extension + "_sha256"],
                     "pixel_check": "unavailable: Pillow not installed"}
            if Image is not None:
                with Image.open(path) as image:
                    image.load()
                    require(image.format == extension.upper(), f"Image signature mismatch: {relative}")
                    require(list(image.size) == dimensions, f"Image dimension mismatch: {relative}")
                    band_height = max(40, int(image.height * .08))
                    footer = image.convert("L").crop((0, image.height - band_height, image.width, image.height))
                    histogram = footer.histogram()
                    total = footer.width * footer.height
                    dark_fraction = sum(histogram[:81]) / total
                    light_fraction = sum(histogram[200:]) / total
                    require(dark_fraction > .25, f"Low-contrast/missing footer panel: {relative}")
                    require(light_fraction > .002 and sum(histogram[200:]) >= 150,
                            f"Missing footer text-like light pixels: {relative}")
                    check.update({"pixel_check": "PASS: footer contrast and light glyph presence",
                                  "dimensions_px": list(image.size), "dark_footer_fraction": round(dark_fraction, 4),
                                  "light_footer_fraction": round(light_fraction, 4)})
            media_checks.append(check)
        changed = item["changed_pages"]
        require(isinstance(changed, list) and changed, f"Missing page placement: {identifier}")
        for page in changed:
            require(page in READERS, f"Unknown reader placement: {page}")
            text = (WIKI / page).read_text(encoding="utf-8")
            require(item["png_path"] in text or item["webp_path"] in text,
                    f"Selected image not used on declared page: {identifier} {page}")
        manual_text_records.append({"source_id": identifier, "expected_visible_text": visible,
                                    "review": item.get("visual_review", "See edition visual-review record"),
                                    "automatic_OCR_performed": False})
    actual_media = {path.resolve() for path in (WIKI / "assets/imagegen-20261115").rglob("*")
                    if path.is_file() and path.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg", ".gif"}}
    require(actual_media == expected_media, "Unregistered or missing editorial media")
    for path in actual_media:
        match = re.match(r"^(\d{2})[_-]", path.name)
        require(match is not None and int(match.group(1)) in ACCEPTED_IDS,
                f"Vetoed/unregistered source ID in published media: {path.name}")

    local_links = 0
    graphics = 0
    for name in READERS:
        require((WIKI / name).is_file(), f"Missing reader page: {name}")
    for page in sorted(WIKI.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        prose = re.sub(r"```.*?```", "", text, flags=re.S)
        prose = re.sub(r"`[^`]*`", "", prose)
        require("**" not in prose and not re.search(r"(?<!_)__(?!_)", prose), f"Bold formatting: {page.name}")
        require(not re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b", prose), f"Unfinished prose: {page.name}")
        if page.name in CHAPTERS:
            require(len(re.findall(r"\b[\w’'-]+\b", text)) >= 850, f"Incomplete chapter: {page.name}")
            require("![" in text, f"Chapter without graphics: {page.name}")
        for match in re.finditer(r"(!?)\[([^\]]*)\]\(([^)\n]+)\)", text):
            image_mark, label, target = match.groups()
            target = target.strip("<>").split(' "', 1)[0]
            parsed = urlparse(target)
            if parsed.scheme:
                require(parsed.scheme in {"https", "http", "mailto"}, f"Unsupported URL scheme: {page.name}: {target}")
                continue
            if not parsed.path:
                continue
            resolved = (page.parent / unquote(parsed.path)).resolve()
            require(resolved.is_relative_to(ROOT.resolve()), f"Link outside repository: {page.name}: {target}")
            relative = resolved.relative_to(ROOT).as_posix()
            body = repository_bytes(relative)
            if parsed.fragment and resolved.suffix == ".md":
                anchors = [heading_anchor(value) for value in re.findall(r"^#+\s+(.+)$", body.decode("utf-8-sig"), re.M)]
                require(parsed.fragment in anchors, f"Missing linked heading: {target}")
            if image_mark:
                require(len(label.strip()) >= 20, f"Uninformative alt text: {page.name}: {target}")
                require(resolved.suffix.lower() in {".png", ".webp", ".gif", ".svg", ".jpg", ".jpeg"},
                        f"Unexpected embedded media: {target}")
                following = text[match.end():].lstrip().split("\n\n", 1)[0]
                require(len(following.strip()) >= 45 and re.search(r"\b(?:Figure|Conceptual)\b", following),
                        f"Missing informative adjacent caption: {page.name}: {target}")
                graphics += 1
            local_links += 1

    if args.require_pixels:
        require(Image is not None, "Pillow is required for requested media pixel checks")
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if Image is not None else "PASS_STATIC_MEDIA_PIXELS_PENDING",
        "schema": manifest["schema"], "baseline_main_sha": base,
        "reader_pages": len(READERS), "chapters": len(CHAPTERS),
        "package_assets_accounted_for": 20, "accepted_source_ids": sorted(ACCEPTED_IDS),
        "excluded_source_ids": sorted(excluded_ids), "new_media_files": len(expected_media),
        "protected_files_verified": len(protected), "original_media_unchanged": 21,
        "original_GIFs_unchanged": original_gifs, "payload_hashes_verified": len(payload_names),
        "local_links_checked": local_links, "embedded_graphics_with_captions": graphics,
        "frozen_base_link_fallbacks": sorted(fallback_links), "media_checks": media_checks,
        "manual_text_review_checklist": manual_text_records,
        "manual_visual_review_record": manifest.get("visual_review", "Not supplied in manifest"),
        "watermark_check_scope": "Footer contrast and light glyph presence; visible wording and scientific claims require recorded visual inspection. No OCR performed.",
        "owner_review_required": True, "owner_review_status": manifest.get("owner_review_status", "pending"),
        "both_AI_declarations_identify_new_collection": True,
        "native_sync_approval_inferred": False,
        "historical_manifests_reinterpreted_or_overwritten": False,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
