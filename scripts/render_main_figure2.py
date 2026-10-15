#!/usr/bin/env python3
"""Render manuscript Figure 2 from aggregate, body-free source data."""

from __future__ import annotations

import csv
import os
from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manuscript" / "source_data"
OUTPUT = ROOT / "manuscript" / "figures" / "figure2_endpoint_preservation"

qa_scripts = os.environ.get("FIGURE_QA_SCRIPTS")
if not qa_scripts:
    raise RuntimeError("FIGURE_QA_SCRIPTS must point to the figure QA scripts")
sys.path.insert(0, qa_scripts)
from audit_panel_alignment import require_matplotlib_panel_alignment  # noqa: E402


CONTROL = "#73849A"
METHOD = "#2468B4"
CORRECTION = "#43A047"
REGRESSION = "#C23B3B"
BOTH_WRONG = "#D7DCE2"
TIED = "#AAB3BE"
DARK = "#1F2933"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "font.size": 6.5,
    "axes.titlesize": 7.2,
    "axes.labelsize": 6.5,
    "xtick.labelsize": 5.8,
    "ytick.labelsize": 6.2,
    "legend.fontsize": 5.8,
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 0.7,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
})


def read_rows(name: str) -> list[dict[str, str]]:
    with (SOURCE / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def panel_label(ax, label: str) -> None:
    ax.annotate(
        label,
        xy=(0, 1),
        xycoords="axes fraction",
        xytext=(-25, 7),
        textcoords="offset points",
        fontsize=8,
        fontweight="bold",
        ha="left",
        va="bottom",
        annotation_clip=False,
    )


def draw_accuracy(ax, rows: list[dict[str, str]]) -> None:
    ypos = {"TSP": (3, 2), "OR-Debug": (1, 0)}
    for row in rows:
        control_y, method_y = ypos[row["study"]]
        control = 100 * float(row["control_accuracy"])
        method = 100 * float(row["method_accuracy"])
        ax.barh(control_y, control, height=0.6, color=CONTROL)
        ax.barh(method_y, method, height=0.6, color=METHOD)
        ax.text(control - 2, control_y, f"{control:.1f}%", color="white", ha="right", va="center", fontsize=6, fontweight="bold")
        ax.text(method - 2, method_y, f"{method:.1f}%", color="white", ha="right", va="center", fontsize=6, fontweight="bold")
        ax.text(method + 2, method_y, f"+{method-control:.1f} pp", color=CORRECTION, ha="left", va="center", fontsize=5.7, fontweight="bold")
        ax.text(-2, control_y, "Control", color=CONTROL, ha="right", va="center", fontsize=5.8)
        ax.text(-2, method_y, "Method", color=METHOD, ha="right", va="center", fontsize=5.8, fontweight="bold")
    ax.set_yticks([2.5, 0.5], ["TSP\n(n=140)", "OR-Debug\n(n=2,845)"])
    ax.set_xlim(-2, 108)
    ax.set_ylim(-0.65, 3.65)
    ax.set_xlabel("Full-denominator accuracy")
    ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
    ax.set_title("Endpoint accuracy", loc="left", fontweight="bold", pad=5)


def draw_paired(ax, rows: list[dict[str, str]]) -> None:
    colors = [CONTROL, CORRECTION, REGRESSION, BOTH_WRONG]
    keys = ["both_correct", "corrections", "regressions", "both_wrong"]
    names = ["Both correct", "Correction", "Regression", "Both wrong"]
    for y, row in enumerate(reversed(rows)):
        total = int(row["denominator"])
        left = 0.0
        for key, color in zip(keys, colors):
            count = int(row[key]); width = 100 * count / total
            if width:
                ax.barh(y, width, left=left, height=0.5, color=color, edgecolor="white", lw=0.5)
                if width >= 12:
                    ax.text(left + width / 2, y, str(count), ha="center", va="center", fontsize=5.6,
                            color="white" if color in (CONTROL, CORRECTION) else DARK, fontweight="bold")
            left += width
        ax.text(100, y - 0.36, "Regression: 0", ha="right", va="top", fontsize=5.5, color=REGRESSION)
    ax.set_yticks([0, 1], ["OR-Debug", "TSP"])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Paired outcome share")
    ax.set_xticks([0, 50, 100], ["0", "50", "100%"])
    ax.set_ylim(-0.65, 1.55)
    ax.set_title("Paired outcomes", loc="left", fontweight="bold", pad=5)
    ax.legend(
        [Patch(facecolor=c) for c in colors],
        names,
        ncol=2,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.48),
        columnspacing=0.8,
        handlelength=1.0,
        handletextpad=1.0,
    )


def draw_groups(ax, rows: list[dict[str, str]]) -> None:
    for y, row in enumerate(reversed(rows)):
        total = int(row["groups"])
        counts = [int(row["positive_groups"]), int(row["tied_groups"]), int(row["negative_groups"])]
        left = 0.0
        for index, (count, color) in enumerate(zip(counts, [CORRECTION, TIED, REGRESSION])):
            width = 100 * count / total
            if width:
                ax.barh(y, width, left=left, height=0.5, color=color, edgecolor="white", lw=0.5)
                if width >= 13:
                    suffix = " positive" if index == 0 else " tied"
                    ax.text(left + width / 2, y, f"{count}{suffix}", ha="center", va="center", fontsize=5.8,
                            color="white" if color == CORRECTION else DARK, fontweight="bold")
            left += width
        ax.text(100, y + 0.35, "0 negative", ha="right", va="bottom", fontsize=5.5, color=REGRESSION)
    ax.set_yticks([0, 1], ["OR-Debug\n100 groups", "TSP\n7 sizes"])
    ax.set_xlim(0, 100)
    ax.set_xlabel("")
    ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
    ax.set_title("Consistency across declared groups", loc="left", fontweight="bold", pad=5)
    ax.text(100, -0.55, "OR-Debug sign test: p=2.71e-20", ha="right", va="top", fontsize=5.6, color=DARK)
    ax.text(0, -0.55, "TSP sizes are descriptive", ha="left", va="top", fontsize=5.6, color="#5D6772")


def draw_identity(ax, rows: list[dict[str, str]]) -> None:
    rows = [row for row in rows if row["family"] != "All"]
    labels = [row["family"] for row in rows]
    y = list(reversed(range(len(rows))))
    ax.barh(y, [100] * len(rows), height=0.48, color=METHOD, edgecolor="white", lw=0.5)
    for yi, row in zip(y, rows):
        ax.text(50, yi, f"{int(row['exact_matches']):,}/{int(row['records']):,}", ha="center", va="center",
                color="white", fontsize=6.2, fontweight="bold")
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 50, 100], ["0", "50", "100%"])
    ax.set_xlabel("Exact output identity")
    ax.set_title("Frozen-interface preservation", loc="left", fontweight="bold", pad=5)
    ax.text(50, -0.72, "2,985/2,985 total\naccuracy not rescored", ha="center", va="top", fontsize=5.8, color=DARK)


def main() -> None:
    endpoint = read_rows("figure2_endpoint_summary.csv")
    groups = read_rows("figure2_group_summary.csv")
    identity = read_rows("figure2_router_identity.csv")
    assert [(row["study"], int(row["denominator"])) for row in endpoint] == [("TSP", 140), ("OR-Debug", 2845)]
    assert sum(int(row["corrections"]) for row in endpoint) == 1970
    assert sum(int(row["regressions"]) for row in endpoint) == 0
    assert int(next(row for row in identity if row["family"] == "All")["exact_matches"]) == 2985

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(7.0866, 4.8031), constrained_layout=True)
    grid = fig.add_gridspec(2, 3, width_ratios=[1.15, 1.15, 1.0], height_ratios=[1, 1])
    axes = {
        "a": fig.add_subplot(grid[0, :2]),
        "b": fig.add_subplot(grid[0, 2]),
        "c": fig.add_subplot(grid[1, :2]),
        "d": fig.add_subplot(grid[1, 2]),
    }
    draw_accuracy(axes["a"], endpoint)
    draw_paired(axes["b"], endpoint)
    draw_groups(axes["c"], groups)
    draw_identity(axes["d"], identity)
    for label, ax in axes.items():
        panel_label(ax, label)
        ax.tick_params(length=2.5, pad=2)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig,
        json_out=str(OUTPUT.with_suffix(".alignment.json")),
        overlay_svg=str(OUTPUT.with_suffix(".alignment.svg")),
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        require_panel_labels=True,
        strict=True,
    )
    fig.savefig(OUTPUT.with_suffix(".pdf"))
    fig.savefig(OUTPUT.with_suffix(".svg"))
    fig.savefig(OUTPUT.with_suffix(".png"), dpi=600)
    fig.savefig(OUTPUT.with_suffix(".tiff"), dpi=600)
    plt.close(fig)


if __name__ == "__main__":
    main()
