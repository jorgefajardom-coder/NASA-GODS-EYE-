"""Static scaffold checks; this is not scientific or ROS acceptance evidence."""

import ast
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    packages = sorted((ROOT / "src").glob("mge_*"))
    for package in packages:
        manifest = ET.parse(package / "package.xml").getroot()
        if manifest.findtext("name") != package.name:
            errors.append(f"package name mismatch: {package}")
        if package.name != "mge_interfaces":
            for path in ("setup.py", "setup.cfg", f"resource/{package.name}",
                         f"{package.name}/__init__.py"):
                if not (package / path).is_file():
                    errors.append(f"missing package file: {package.name}/{path}")
    for directory in ("src", "scripts", "tests"):
        for path in (ROOT / directory).rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for path in (ROOT / "data").rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "docs/ai_usage.json").read_text(encoding="utf-8"))
    for item in metadata["uses"]:
        for scope in item["paths"]:
            if not (ROOT / scope).exists():
                errors.append(f"AI disclosure points to missing path: {scope}")
    for doc in [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]:
        for target in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            path = target.split("#", 1)[0]
            if not (doc.parent / path).exists():
                errors.append(f"broken local link in {doc.name}: {target}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Static scaffold checks passed ({len(packages)} ROS package manifests).")


if __name__ == "__main__":
    main()
