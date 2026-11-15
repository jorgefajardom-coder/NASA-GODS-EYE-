"""Render the proposed science tree from tree.json; no runtime/mission inputs.

Generation needs Pillow; --check uses only the Python standard library.
AI-use disclosure: OpenAI Codex assisted this documentation/diagram renderer.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
DOC = HERE.parents[1] / "science_extension_tree.md"
PNG = HERE / "science-tree.png"
SVG = HERE / "science-tree.svg"
WIDTH, HEIGHT = 2700, 1840


def load():
    data = json.loads((HERE / "tree.json").read_text(encoding="utf-8"))
    nodes = data["nodes"]
    by_id = {n["id"]: n for n in nodes}
    assert len(nodes) == len(by_id) == 22
    assert {n["id"] for n in nodes} == {f"G{i}" for i in range(4)} | {
        f"{letter}{i}" for letter in "ABCDEF" for i in range(1, 4)}
    active, done = set(), set()

    def visit(key):
        assert key in by_id and key not in active, f"Missing dependency/cycle: {key}"
        if key in done:
            return
        active.add(key)
        for parent in by_id[key]["requires"]:
            visit(parent)
        active.remove(key)
        done.add(key)

    def depends(key, target):
        return key == target or any(depends(p, target) for p in by_id[key]["requires"])

    for node in nodes:
        visit(node["id"])
        for field in ("title", "lead", "status", "question", "relevance", "scope", "acceptance", "stop"):
            assert isinstance(node[field], str) and node[field].strip(), (node["id"], field)
        assert node["reviewers"] and len(set(node["requires"])) == len(node["requires"])
        if not node["id"].startswith("G"):
            assert depends(node["id"], "G3"), f"Extension bypasses G3: {node['id']}"
    digest = hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()
    return data, by_id, digest


def markdown(data, digest):
    out = ["# Science extension tree", "",
           "<!-- Generated from assets/science-tree/tree.json; source_sha256=" + digest + " -->", "",
           "Owner-requested research guide, recorded 14 November 2026 (America/Bogota).",
           f"Publication input: main `{data['source_main']}`. This is a proposed capability/dependency",
           "tree, not a bibliometric ranking, runtime contract, implementation claim or approved research programme.", "",
           "![Proposed science extension tree: four common gates and six branches with three extensions each. Every Requires label is an AND prerequisite. Delivery freeze remains active.](assets/science-tree/science-tree.png)", "",
           "[Scalable image](assets/science-tree/science-tree.svg) · [structured source](assets/science-tree/tree.json)", "",
           "## Freeze and local ideas: owner clarification", "",
           "[D-DEL-03](decisions/2026-11-14-delivery-freeze.md) remains active. This document does not reopen",
           "integration, change the 15 November 20:00 delivery target or approve maps, profiles, budgets,",
           "extra agents or new models. Scientific and contract gates remain unchanged.", "",
           "**If a team member thinks of an extension not covered here, they may evaluate it in an isolated",
           "local branch and bring it for discussion tomorrow, 15 November 2026, America/Bogota.**",
           "This explicitly permitted, bounded local assessment is not permission to push an extension,",
           "merge/deploy it, replace the frozen baseline or mark its prerequisites accepted. Preserve",
           "other members' work and label any local MOCK/synthetic inputs. Do not let a local experiment",
           "displace assigned delivery work. Review time/channel are not scheduled by this guide.", "",
           "Bring a short proposal: question, expected usefulness, required parent milestones, smallest",
           "experiment, source/assumptions, result or blocker, regression risk, owner and decision requested.",
           "Do not force a new idea into an existing node if it needs different evidence. David reviews",
           "scientific value/assumptions and Jesus integration; the owner decides scope. A discussion",
           "tomorrow does not automatically open implementation, even if the idea is attractive.", "",
           "## Reading the tree and choosing worthwhile work", "",
           "The evidenced root is narrower human kinematic MOCK recovery and same-run replay, not complete",
           "scientific three-role execution. [Delivery evidence](delivery_closure_plan.md),",
           "[baseline](CONTRACT_BASELINE.md), [ICD](ICD.md) and [D-COST-02](decisions/2026-11-14-shared-scientific-cost-api.md)",
           "retain their actual publication/approval status. No G0-G3 or extension milestone is marked",
           "accepted by adding this document or by generating its image.", "",
           "All dependencies are **AND**, including cross-branch prerequisites. Every extension depends",
           "transitively on G3; a new operational trial needs accepted prerequisites plus an explicit scope",
           "decision. A local feasibility assessment may identify blockers without accepting any gate.", "",
           "A prerequisite is an evidenced need/capability, not an obligation to add architecture. If the",
           "unchanged baseline already meets a required target, record that result and review the relevant",
           "dependency before advancing. Do not mark an unimplemented feature complete or implement an",
           "unnecessary optimizer merely to tick a node. Amend this proposed graph through review when a",
           "dependency proves inappropriate; never silently bypass it.", "",
           "After the base is accepted and scope is reopened, A1 (representative context), B1 (robustness)",
           "and D1 (representative time/resources) are first candidates, not simultaneous commitments.",
           "Choose the one addressing a measured weakness. C1/F1 then test the value of coordination/",
           "acquired information. E1/E2 are conditional on measured computation bottlenecks. The third",
           "levels are long-term horizons; their presence is permission to discuss an idea, not a task order.", "",
           "### Advancement contract", "",
           "1. Name one question and a measured baseline weakness; freeze the control revision/inputs.",
           "2. Accept every required parent with linked evidence and reviewers; decide the bounded scope.",
           "3. Before evaluation, declare metrics, N, tolerances, pass/fail and stop conditions.",
           "4. Retain source/config/model/input hashes, seeds, commands, environment, observed results and failures.",
           "5. Pass a positive case, a negative/adversarial case, an independent check and existing regressions.",
           "6. Lead supplies evidence; named reviewers assess it and the owner accepts/rejects scope before expansion.", "",
           "Evidence states: proposed -> prerequisites reviewed -> bounded trial -> evidence reviewed ->",
           "accepted for its declared scope, or rejected/deferred. A correct negative result closes an experiment",
           "but does not establish a capability it failed to demonstrate. No deadline, green build, appearance",
           "or arbitrary complexity level substitutes for that decision. Increase one experimental axis at a time.", "",
           "## Complete dependency graph", "", "```mermaid", "flowchart TD"]
    for n in data["nodes"]:
        out.append(f'  {n["id"]}["{n["id"]}: {n["title"]}"]')
    for n in data["nodes"]:
        for parent in n["requires"]:
            out.append(f'  {parent} --> {n["id"]}')
    out += ["```", "", "The image emphasizes branch progression and prints each immediate Requires set.",
            "The graph/structured source preserve every cross-link; no branch bypasses the common gates.", "",
            "## Milestones and extension contracts", ""]
    for n in data["nodes"]:
        requires = ", ".join(n["requires"]) or "Explicit scope decision under D-DEL-03"
        out += [f'### {n["id"]} — {n["title"]}', "",
                f'- **Lead:** {n["lead"]}. **Reviewers:** {", ".join(n["reviewers"])}.',
                f'- **Requires (AND):** {requires}. **State:** `{n["status"]}`.',
                f'- **Priority/value:** {n["priority"]}. {n["relevance"]}',
                f'- **Question:** {n["question"]}', f'- **Initial scope:** {n["scope"]}',
                f'- **Verifiable milestone:** {n["acceptance"]}',
                f'- **Stop / limit:** {n["stop"]}', ""]
    out += ["## Provenance, interpretation and reproduction", "",
            "Use the [NASA lineage register](nasa_traceability.md) for actual product IDs, native resolution,",
            "processing/CRS/datum, uncertainty, hashes and source-to-decision claims. Ground truth/future",
            "discoveries stay isolated; synthetic details never become NASA observations. H-DAN-01 remains",
            "a proposed seeded-world experiment, not proof of learned adaptation or simulation-to-Mars transfer.", "",
            "No specific new study, algorithm, hardware capability or numeric safety threshold is approved",
            "here. Each node's proposed benefit is a hypothesis for this project. Physical/operational claims",
            "require additional expert and institutional validation. Preserve labels and required AI disclosures.", "",
            "The image is an AI-assisted, code-rendered planning diagram, not a terrain image. Its visible",
            "AI-generated marking and metadata must survive export. It contains no NASA logos/mission marks.", "",
            "The Markdown, PNG and SVG are rendered from one JSON source; do not manually change generated",
            "copies. To update a node, edit the source, render, inspect both images and check dependencies:", "",
            "```sh", "# Rendering needs Python with Pillow; --check uses only the standard library.",
            "python docs/assets/science-tree/render.py", "python docs/assets/science-tree/render.py --check", "```", "",
            "The check verifies all 22 nodes, an acyclic graph, G3 ancestry, document/source parity, image",
            "dimensions and provenance/watermark declarations. Visual inspection separately checks legibility.",
            "This documentation changes no ROS/replay/runtime schema, receipt or scientific approval.", ""]
    return "\n".join(out)


def draw(data, digest):
    from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

    image = Image.new("RGB", (WIDTH, HEIGHT), "#f5f3ed")
    pen = ImageDraw.Draw(image)
    font_candidates = [Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    font_path = next((p for p in font_candidates if p.exists()), None)
    if font_path is None:
        raise RuntimeError("Install Arial or DejaVu Sans for reproducible readable diagram text")
    fonts = {s: ImageFont.truetype(str(font_path), s) for s in (24, 27, 29, 33, 39, 58)}
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
           '<title id="title">Science extension tree</title>',
           '<desc id="desc">Four prerequisite gates and eighteen proposed extensions. Every Requires list is AND. Delivery freeze remains active; isolated local assessment of unlisted ideas may be discussed on 15 November.</desc>',
           f'<metadata>{html.escape(json.dumps({"source_sha256":digest,"ai_use":data["ai_use"],"kind":data["kind"]}))}</metadata>']

    def rect(box, fill, stroke=None, radius=0):
        pen.rounded_rectangle(box, radius=radius, fill=fill, outline=stroke, width=2)
        x, y, x2, y2 = box
        svg.append(f'<rect x="{x}" y="{y}" width="{x2-x}" height="{y2-y}" rx="{radius}" fill="{fill}" stroke="{stroke or "none"}" stroke-width="2"/>')

    def line(points, color="#82949b", width=3, arrow=False):
        pen.line(points, fill=color, width=width)
        coords = " ".join(f"{x},{y}" for x, y in points)
        svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}"/>')
        if arrow:
            x, y = points[-1]
            x0, y0 = points[-2]
            triangle = [(x, y), (x-9, y-14), (x+9, y-14)] if y > y0 else [(x, y), (x-14, y-9), (x-14, y+9)]
            pen.polygon(triangle, fill=color)
            svg.append(f'<polygon points="{" ".join(f"{a},{b}" for a,b in triangle)}" fill="{color}"/>')

    def text(value, x, y, size=29, color="#173d49"):
        pen.text((x, y), value, font=fonts[size], fill=color, anchor="lt")
        svg.append(f'<text x="{x}" y="{y+size}" font-family="Arial,DejaVu Sans,sans-serif" font-size="{size}" fill="{color}">{html.escape(value)}</text>')

    def wrapped(value, x, y, width, size=33, max_lines=3):
        words, rows, row = value.split(), [], ""
        for word in words:
            trial = (row + " " + word).strip()
            if pen.textlength(trial, font=fonts[size]) > width and row:
                rows.append(row)
                row = word
            else:
                row = trial
        if row:
            rows.append(row)
        assert len(rows) <= max_lines, (value, rows)
        for i, value in enumerate(rows):
            text(value, x, y+i*(size+8), size)

    rect((0, 0, WIDTH, HEIGHT), "#f5f3ed")
    text("SCIENCE EXTENSION TREE", 65, 48, 58)
    text("Proposed capabilities | delivery freeze active | no milestone accepted by this diagram", 65, 128, 29)
    text("Current root: recorded human MOCK recovery + replay; full scientific three-role closure remains open.", 65, 181, 29)
    nodes = {n["id"]: n for n in data["nodes"]}
    gate_x = [65, 725, 1385, 2045]
    for i in range(3):
        line([(gate_x[i]+585, 331), (gate_x[i+1]-7, 331)], arrow=True)
    for i in range(4):
        n, x = nodes[f"G{i}"], gate_x[i]
        rect((x, 250, x+585, 415), "#dce8e7", "#90aaa9", 14)
        text(n["id"], x+22, 270, 39)
        text(n["title"], x+22, 323, 33)
        text("Lead: "+n["lead"]+" | Requires: "+(", ".join(n["requires"]) or "scope decision"), x+22, 376, 24)
    text("ALL extensions require G3 transitively. Every additional Requires list must also be satisfied (AND).", 65, 462, 29)
    text("Read left-to-right within the trunk; top-to-bottom within each branch. Cross-branch links are printed on nodes.", 65, 510, 27)
    left, step, card_w = 65, 440, 395
    for index, branch in enumerate(data["branches"]):
        x = left+index*step
        wrapped(branch["title"], x, 575, card_w, 33, 2)
        for j in range(3):
            key, y = branch["id"]+str(j+1), 690+j*255
            if j < 2:
                line([(x+card_w/2, y+224), (x+card_w/2, y+248)], arrow=True)
            n = nodes[key]
            rect((x, y, x+card_w, y+224), "#ffffff", "#c2cdcc", 10)
            text(key, x+20, y+17, 39, "#975431")
            wrapped(n["title"], x+20, y+73, card_w-40, 33, 2)
            text("Lead: "+n["lead"], x+20, y+165, 27)
            text("Requires: "+", ".join(n["requires"]), x+20, y+199, 24)
    text("Review is not implementation approval. An accepted experiment opens only its declared scope.", 65, 1480, 29)
    text("New unlisted idea? Assess in an isolated local branch; discuss on 15 Nov 2026 (America/Bogota).", 65, 1530, 29)
    text("No extension push, merge, deployment or frozen-baseline change is authorized by that local assessment.", 65, 1578, 27)
    text("Evidence: reproducible artifact + positive/negative checks + independent review + green regressions + scope decision.", 65, 1642, 27)
    text("Authoritative contracts, reviewers and stop conditions: docs/science_extension_tree.md", 65, 1690, 27)
    text("AI-generated | planning diagram, not NASA observational data", 65, 1770, 29, "#975431")
    text("Source "+digest[:16], 2190, 1770, 24)
    svg.append("</svg>")
    SVG.write_text("\n".join(svg)+"\n", encoding="utf-8")
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Description", "AI-generated planning diagram; no NASA observational data or branding")
    meta.add_text("AI-use", json.dumps(data["ai_use"]))
    meta.add_text("Source-sha256", digest)
    image.save(PNG, pnginfo=meta, optimize=True)


def check(data, digest):
    assert DOC.read_text(encoding="utf-8") == markdown(data, digest)
    svg = SVG.read_text(encoding="utf-8")
    assert digest in svg and "AI-generated" in svg
    tree = ET.fromstring(svg)
    assert tree.attrib["width"] == str(WIDTH) and tree.attrib["height"] == str(HEIGHT)
    for node in data["nodes"]:
        assert f'>{node["id"]}</text>' in svg, node["id"]
    raw, texts = PNG.read_bytes(), {}
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", raw[16:24]) == (WIDTH, HEIGHT)
    offset = 8
    while offset < len(raw):
        size = struct.unpack(">I", raw[offset:offset+4])[0]
        if raw[offset+4:offset+8] == b"tEXt":
            k, v = raw[offset+8:offset+8+size].split(b"\0", 1)
            texts[k.decode()] = v.decode()
        offset += 12+size
    assert texts["Source-sha256"] == digest
    assert "AI-generated" in texts["Description"]
    assert json.loads(texts["AI-use"])["tool"] == "OpenAI Codex"
    expected = {n["id"] for n in data["nodes"]}
    assert set(re.findall(r"^### ([A-FG][0-3]) ", DOC.read_text(encoding="utf-8"), re.M)) == expected
    print("Verified 22 nodes, acyclic AND dependencies, G3 ancestry, generated document, SVG/PNG metadata and dimensions.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data, _, digest = load()
    if not args.check:
        DOC.write_text(markdown(data, digest), encoding="utf-8")
        draw(data, digest)
    check(data, digest)


if __name__ == "__main__":
    main()
