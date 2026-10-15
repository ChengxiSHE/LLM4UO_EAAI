#!/usr/bin/env python3
"""Repository-local, dependency-free panel-alignment gate.

The core auditor consumes physical panel rectangles expressed in points.  The
Matplotlib adapter is imported only when a renderer calls it, so the self-test
and stored-layout checks remain runnable in the credential-free evidence layer.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
import html
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_TOLERANCE_PT = 1.5
DEFAULT_GUTTER_TOLERANCE_PT = 1.5


class PanelAlignmentError(RuntimeError):
    """Raised when a required alignment check is blocking."""


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _bbox(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 4:
        raise ValueError("bbox_pt must contain four numbers")
    box = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in box):
        raise ValueError("bbox_pt values must be finite")
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("bbox_pt must have positive width and height")
    return box


def _groups(panels: Sequence[Mapping[str, Any]], orientation: str) -> list[dict[str, Any]]:
    if orientation == "row":
        fields = ("grid_id", "row_start", "row_stop")
    else:
        fields = ("grid_id", "col_start", "col_stop")
    grouped: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for panel in panels:
        key = tuple(panel.get(field) for field in fields)
        if any(value is None for value in key):
            continue
        grouped[key].append(str(panel["id"]))
    return [
        {"id": f"inferred-{orientation}-{index}", "panels": ids}
        for index, ids in enumerate((ids for ids in grouped.values() if len(ids) >= 2), 1)
    ]


def _spread(values: Sequence[float]) -> float:
    return max(values) - min(values) if values else 0.0


def _not_auditable(errors: Sequence[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "auditable": False,
        "verdict": "NOT AUDITABLE",
        "summary": {"fail": 0, "warn": 0, "comparisons": 0, "exemptions": 0},
        "errors": list(errors),
        "findings": [],
    }


def audit_layout_manifest(
    manifest: Mapping[str, Any],
    *,
    tolerance_pt: float = DEFAULT_TOLERANCE_PT,
    gutter_tolerance_pt: float = DEFAULT_GUTTER_TOLERANCE_PT,
    require_panel_labels: bool = False,
) -> dict[str, Any]:
    """Check shared row/column edges and panel-label anchors in physical points."""
    if tolerance_pt < 0 or gutter_tolerance_pt < 0:
        raise ValueError("alignment tolerances must be non-negative")
    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    figure = manifest.get("figure")
    if not isinstance(figure, Mapping):
        errors.append("figure must be an object")
        figure = {}
    try:
        width_pt = float(figure["width_pt"])
        height_pt = float(figure["height_pt"])
        if min(width_pt, height_pt) <= 0 or not all(map(math.isfinite, (width_pt, height_pt))):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        errors.append("figure dimensions must be positive finite numbers")
        width_pt = height_pt = 0.0

    raw_panels = manifest.get("panels")
    if not isinstance(raw_panels, Sequence) or isinstance(raw_panels, (str, bytes)):
        errors.append("panels must be a list")
        raw_panels = []
    panels: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_panels, 1):
        if not isinstance(raw, Mapping):
            errors.append(f"panel {index} must be an object")
            continue
        panel_id = str(raw.get("id") or "").strip()
        if not panel_id:
            errors.append(f"panel {index} is missing id")
            continue
        try:
            box = _bbox(raw.get("bbox_pt"))
        except (TypeError, ValueError) as exc:
            errors.append(f"panel {panel_id}: {exc}")
            continue
        if box[0] < -0.01 or box[1] < -0.01 or box[2] > width_pt + 0.01 or box[3] > height_pt + 0.01:
            errors.append(f"panel {panel_id} extends beyond the figure")
        panel = dict(raw)
        panel["id"] = panel_id
        panel["bbox_pt"] = list(box)
        anchor = panel.get("panel_label_anchor_pt")
        if anchor is not None:
            try:
                anchor = [float(value) for value in anchor]
                if len(anchor) != 2 or not all(map(math.isfinite, anchor)):
                    raise ValueError
                panel["panel_label_anchor_pt"] = anchor
            except (TypeError, ValueError):
                errors.append(f"panel {panel_id} has an invalid label anchor")
        panels.append(panel)
    ids = [panel["id"] for panel in panels]
    if len(ids) != len(set(ids)):
        errors.append("panel ids must be unique")
    if not panels:
        errors.append("at least one panel is required")
    if errors:
        return _not_auditable(errors)

    layout = {
        "schema_version": SCHEMA_VERSION,
        "backend": str(manifest.get("backend") or "unknown"),
        "figure": {"width_pt": width_pt, "height_pt": height_pt},
        "panels": panels,
        "row_groups": list(manifest.get("row_groups") or _groups(panels, "row")),
        "column_groups": list(manifest.get("column_groups") or _groups(panels, "column")),
        "boundary_groups": [],
        "exemptions": list(manifest.get("exemptions") or []),
    }
    if len(panels) == 1:
        return {
            "schema_version": SCHEMA_VERSION,
            "applicable": False,
            "auditable": False,
            "verdict": "NOT APPLICABLE",
            "backend": layout["backend"],
            "summary": {"fail": 0, "warn": 0, "comparisons": 0, "exemptions": 0},
            "tolerances": {"alignment_pt": tolerance_pt, "gutter_pt": gutter_tolerance_pt},
            "layout": layout,
            "findings": [],
        }

    by_id = {panel["id"]: panel for panel in panels}
    findings: list[dict[str, Any]] = []
    comparisons = 0
    for orientation, group_name in (("row", "row_groups"), ("column", "column_groups")):
        for group in layout[group_name]:
            group_ids = [str(value) for value in group.get("panels", [])]
            if len(group_ids) < 2 or any(value not in by_id for value in group_ids):
                findings.append({
                    "severity": "FAIL",
                    "kind": "invalid-comparison-group",
                    "group": str(group.get("id") or "unknown"),
                    "panels": group_ids,
                    "message": "Comparison group must contain at least two known panels",
                })
                continue
            comparisons += 1
            boxes = {panel_id: _bbox(by_id[panel_id]["bbox_pt"]) for panel_id in group_ids}
            if orientation == "row":
                metrics = {
                    "top": [box[3] for box in boxes.values()],
                    "bottom": [box[1] for box in boxes.values()],
                    "height": [box[3] - box[1] for box in boxes.values()],
                }
            else:
                metrics = {
                    "left": [box[0] for box in boxes.values()],
                    "right": [box[2] for box in boxes.values()],
                    "width": [box[2] - box[0] for box in boxes.values()],
                }
            if max(_spread(values) for values in metrics.values()) > tolerance_pt:
                findings.append({
                    "severity": "FAIL",
                    "kind": f"{orientation}-axes-misalignment",
                    "group": str(group.get("id") or "unknown"),
                    "panels": group_ids,
                    "tolerance_pt": tolerance_pt,
                    "metrics": metrics,
                    "message": f"Panels in one {orientation} do not share their physical axes geometry",
                })
            anchors = {
                panel_id: by_id[panel_id].get("panel_label_anchor_pt") for panel_id in group_ids
            }
            missing = [panel_id for panel_id, anchor in anchors.items() if anchor is None]
            if require_panel_labels and missing:
                findings.append({
                    "severity": "WARN",
                    "kind": "panel-label-not-auditable",
                    "group": str(group.get("id") or "unknown"),
                    "panels": missing,
                    "message": "Comparable panels are missing top-left label anchors",
                })
            present = {panel_id: anchor for panel_id, anchor in anchors.items() if anchor is not None}
            if len(present) >= 2:
                coordinate = 1 if orientation == "row" else 0
                if _spread([float(anchor[coordinate]) for anchor in present.values()]) > tolerance_pt:
                    findings.append({
                        "severity": "FAIL",
                        "kind": f"{orientation}-panel-label-misalignment",
                        "group": str(group.get("id") or "unknown"),
                        "panels": list(present),
                        "message": f"Panel-label anchors are not aligned within the {orientation}",
                    })

    failures = sum(item["severity"] == "FAIL" for item in findings)
    warnings = sum(item["severity"] == "WARN" for item in findings)
    verdict = "FIX BEFORE DELIVERY" if failures else "REVIEW REQUIRED" if warnings else "PASS"
    return {
        "schema_version": SCHEMA_VERSION,
        "applicable": True,
        "auditable": True,
        "verdict": verdict,
        "backend": layout["backend"],
        "summary": {
            "fail": failures,
            "warn": warnings,
            "comparisons": comparisons,
            "exemptions": len(layout["exemptions"]),
        },
        "tolerances": {"alignment_pt": tolerance_pt, "gutter_pt": gutter_tolerance_pt},
        "layout": layout,
        "findings": findings,
    }


def exit_code(report: Mapping[str, Any], *, strict: bool = False) -> int:
    if not report.get("auditable") and report.get("verdict") != "NOT APPLICABLE":
        return 2
    if report.get("summary", {}).get("fail", 0):
        return 1
    if strict and report.get("summary", {}).get("warn", 0):
        return 1
    return 0


def write_json_report(report: Mapping[str, Any], path: str | Path) -> None:
    _atomic_write(Path(path), json.dumps(report, indent=2, ensure_ascii=False) + "\n")


def write_overlay_svg(report: Mapping[str, Any], path: str | Path) -> None:
    layout = report.get("layout")
    if not isinstance(layout, Mapping):
        raise ValueError("report has no auditable layout")
    width = float(layout["figure"]["width_pt"])
    height = float(layout["figure"]["height_pt"])
    rows = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}pt" height="{height}pt" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
    ]
    for panel in layout["panels"]:
        left, bottom, right, top = _bbox(panel["bbox_pt"])
        y = height - top
        rows.append(
            f'<rect x="{left}" y="{y}" width="{right-left}" height="{top-bottom}" '
            'fill="none" stroke="#2468B4" stroke-width="0.8"/>'
        )
        rows.append(
            f'<text x="{left+3}" y="{y+10}" font-size="8" fill="#25313C">'
            f'{html.escape(str(panel["id"]))}</text>'
        )
    rows.append("</svg>")
    _atomic_write(Path(path), "\n".join(rows) + "\n")


def _panel_label_anchor(axis: Any, panel_id: str, width_pt: float, height_pt: float) -> list[float] | None:
    for text in axis.texts:
        if str(text.get_text()).strip() != panel_id:
            continue
        try:
            display = text.get_transform().transform(text.get_position())
            width_px, height_px = axis.figure.canvas.get_width_height()
            return [float(display[0]) * width_pt / width_px, float(display[1]) * height_pt / height_px]
        except Exception:
            continue
    return None


def matplotlib_layout_manifest(fig: Any) -> dict[str, Any]:
    """Measure visible Matplotlib subplot axes after the final layout draw."""
    fig.canvas.draw()
    width_in, height_in = (float(value) for value in fig.get_size_inches())
    width_pt, height_pt = width_in * 72.0, height_in * 72.0
    panels: list[dict[str, Any]] = []
    grid_ids: dict[int, str] = {}
    for index, axis in enumerate(axis for axis in fig.axes if axis.get_visible()):
        try:
            spec = axis.get_subplotspec()
        except AttributeError:
            spec = None
        if spec is None:
            continue
        panel_id = chr(ord("a") + index)
        position = axis.get_position(original=False)
        grid_key = id(spec.get_gridspec())
        grid_ids.setdefault(grid_key, f"matplotlib-grid-{len(grid_ids)+1}")
        panel = {
            "id": panel_id,
            "bbox_pt": [
                float(position.x0 * width_pt),
                float(position.y0 * height_pt),
                float(position.x1 * width_pt),
                float(position.y1 * height_pt),
            ],
            "grid_id": grid_ids[grid_key],
            "row_start": int(spec.rowspan.start),
            "row_stop": int(spec.rowspan.stop),
            "col_start": int(spec.colspan.start),
            "col_stop": int(spec.colspan.stop),
        }
        anchor = _panel_label_anchor(axis, panel_id, width_pt, height_pt)
        if anchor is not None:
            panel["panel_label"] = panel_id
            panel["panel_label_anchor_pt"] = anchor
        panels.append(panel)
    return {
        "schema_version": SCHEMA_VERSION,
        "backend": "python-matplotlib",
        "figure": {"width_pt": width_pt, "height_pt": height_pt},
        "panels": panels,
        "exemptions": [],
    }


def require_matplotlib_panel_alignment(
    fig: Any,
    *,
    json_out: str | Path | None = None,
    overlay_svg: str | Path | None = None,
    tolerance_pt: float = DEFAULT_TOLERANCE_PT,
    gutter_tolerance_pt: float = DEFAULT_GUTTER_TOLERANCE_PT,
    require_panel_labels: bool = False,
    strict: bool = False,
    **_unused: Any,
) -> dict[str, Any]:
    report = audit_layout_manifest(
        matplotlib_layout_manifest(fig),
        tolerance_pt=tolerance_pt,
        gutter_tolerance_pt=gutter_tolerance_pt,
        require_panel_labels=require_panel_labels,
    )
    if json_out is not None:
        write_json_report(report, json_out)
    if overlay_svg is not None and report.get("layout"):
        write_overlay_svg(report, overlay_svg)
    if exit_code(report, strict=strict):
        raise PanelAlignmentError(json.dumps(report, ensure_ascii=False))
    return report


def _self_test() -> None:
    layout = {
        "schema_version": 1,
        "backend": "self-test",
        "figure": {"width_pt": 300, "height_pt": 200},
        "panels": [
            {"id": "a", "bbox_pt": [20, 110, 130, 180], "grid_id": "g", "row_start": 0, "row_stop": 1, "col_start": 0, "col_stop": 1},
            {"id": "b", "bbox_pt": [170, 110, 280, 180], "grid_id": "g", "row_start": 0, "row_stop": 1, "col_start": 1, "col_stop": 2},
            {"id": "c", "bbox_pt": [20, 20, 130, 90], "grid_id": "g", "row_start": 1, "row_stop": 2, "col_start": 0, "col_stop": 1},
            {"id": "d", "bbox_pt": [170, 20, 280, 90], "grid_id": "g", "row_start": 1, "row_stop": 2, "col_start": 1, "col_stop": 2},
        ],
    }
    if exit_code(audit_layout_manifest(layout)) != 0:
        raise AssertionError("aligned layout did not pass")
    shifted = json.loads(json.dumps(layout))
    shifted["panels"][1]["bbox_pt"][1] -= 4
    if exit_code(audit_layout_manifest(shifted)) != 1:
        raise AssertionError("shifted layout did not fail")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json-out")
    parser.add_argument("--overlay-svg")
    parser.add_argument("--require-panel-labels", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("Panel alignment self-test: PASS")
        return 0
    if not args.layout:
        parser.error("layout is required unless --self-test is used")
    try:
        report = audit_layout_manifest(
            json.loads(Path(args.layout).read_text(encoding="utf-8")),
            require_panel_labels=args.require_panel_labels,
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        report = _not_auditable([str(exc)])
    if args.json_out:
        write_json_report(report, args.json_out)
    if args.overlay_svg and report.get("layout"):
        write_overlay_svg(report, args.overlay_svg)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return exit_code(report, strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
