#!/usr/bin/env python3
"""Render manuscript Figure 1: proof-carrying knowledge compilation."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "manuscript" / "figures" / "figure1_knowledge_compilation"

qa_scripts = os.environ.get("FIGURE_QA_SCRIPTS")
if not qa_scripts:
    raise RuntimeError("FIGURE_QA_SCRIPTS must point to the figure QA scripts")
sys.path.insert(0, qa_scripts)
from audit_panel_alignment import require_matplotlib_panel_alignment  # noqa: E402


METHOD = "#2468B4"
METHOD_LIGHT = "#E7F0FA"
TRUSTED = "#25313C"
NEUTRAL = "#6F7D8C"
LIGHT = "#EEF1F4"
CORRECTION = "#43A047"
CORRECTION_LIGHT = "#E8F5E9"
REGRESSION = "#C23B3B"
REGRESSION_LIGHT = "#FBEAEA"
CONDITIONAL = "#D98E24"
CONDITIONAL_LIGHT = "#FFF4DD"
WHITE = "#FFFFFF"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "font.size": 6.3,
    "axes.titlesize": 7.2,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
})


def panel_label(ax, label: str) -> None:
    ax.annotate(
        label,
        xy=(0, 1),
        xycoords="axes fraction",
        xytext=(-19, 5),
        textcoords="offset points",
        fontsize=8,
        fontweight="bold",
        ha="left",
        va="bottom",
        annotation_clip=False,
    )


def box(
    ax,
    xy: tuple[float, float],
    width: float,
    height: float,
    text: str,
    *,
    face: str = WHITE,
    edge: str = TRUSTED,
    linestyle: str = "-",
    linewidth: float = 0.8,
    fontsize: float = 5.4,
    weight: str = "normal",
    radius: float = 0.018,
    zorder: int = 2,
) -> FancyBboxPatch:
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        facecolor=face,
        edgecolor=edge,
        linestyle=linestyle,
        linewidth=linewidth,
        zorder=zorder,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color=TRUSTED,
        zorder=zorder + 1,
        linespacing=1.25,
    )
    return patch


def arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = TRUSTED,
    style: str = "-|>",
    connection: str = "arc3",
    linewidth: float = 0.8,
    zorder: int = 3,
) -> FancyArrowPatch:
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle=style,
        mutation_scale=7,
        color=color,
        linewidth=linewidth,
        connectionstyle=connection,
        shrinkA=1.5,
        shrinkB=1.5,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def tag(ax, x: float, y: float, text: str, color: str, face: str) -> None:
    box(ax, (x, y), 0.24, 0.075, text, face=face, edge=color, fontsize=5.2, weight="bold")


def setup_panel(ax, title: str, label: str) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title(title, loc="left", pad=5, fontweight="bold")
    panel_label(ax, label)


def draw_library(ax) -> None:
    setup_panel(ax, "Typed skill and versioned library", "a")
    tag(ax, 0.73, 0.89, "FORMAL OBJECT", METHOD, METHOD_LIGHT)

    box(
        ax,
        (0.02, 0.53),
        0.26,
        0.22,
        "Untrusted proposer\nLLM · human · search",
        face=WHITE,
        edge=NEUTRAL,
        linestyle="--",
        fontsize=5.4,
        weight="bold",
    )
    ax.text(0.15, 0.49, "cannot edit the\ncorrectness boundary", ha="center", va="top", fontsize=5.1, color=NEUTRAL)

    boundary = FancyBboxPatch(
        (0.34, 0.14),
        0.63,
        0.68,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor="#FAFBFC",
        edgecolor=TRUSTED,
        linewidth=1.1,
        zorder=1,
    )
    ax.add_patch(boundary)
    ax.text(0.655, 0.78, "Trusted library boundary", ha="center", va="center", fontsize=5.8, fontweight="bold", color=TRUSTED)

    box(ax, (0.39, 0.43), 0.53, 0.28,
        "Skill  k = (g, e, t, v, r, p)\npublic guard · typed evidence\ntransform · semantic verifier\nresource checker · provenance",
        face=METHOD_LIGHT, edge=METHOD, fontsize=5.4, weight="bold")
    box(ax, (0.39, 0.20), 0.53, 0.18,
        "Library  L_t\nskills · public router · trusted verifier\nfrozen endpoint · lineage ledger",
        face=WHITE, edge=TRUSTED, fontsize=5.4)
    arrow(ax, (0.28, 0.64), (0.39, 0.59), color=METHOD)
    ax.text(0.655, 0.075, "Canonical manifest implemented · retrospective artifact measure", ha="center", va="center", fontsize=5.0, color=NEUTRAL)


def draw_construction(ax) -> None:
    setup_panel(ax, "Counterexample-guided construction", "b")
    tag(ax, 0.73, 0.89, "FINITE DOMAIN", METHOD, METHOD_LIGHT)

    box(ax, (0.03, 0.68), 0.22, 0.13, "Development\nfailure obligation", face=LIGHT, edge=NEUTRAL, fontsize=5.4, weight="bold")
    box(ax, (0.31, 0.68), 0.20, 0.13, "Finite typed\ngrammar  H_b", face=METHOD_LIGHT, edge=METHOD, fontsize=5.4, weight="bold")
    box(ax, (0.57, 0.68), 0.18, 0.13, "Candidate", face=METHOD_LIGHT, edge=METHOD, fontsize=5.4, weight="bold")
    diamond = Polygon([(0.86, 0.85), (0.99, 0.745), (0.86, 0.64), (0.73, 0.745)], closed=True,
                      facecolor=WHITE, edgecolor=TRUSTED, linewidth=0.9, zorder=2)
    ax.add_patch(diamond)
    ax.text(0.86, 0.745, "semantic\n+ resource\nchecks", ha="center", va="center", fontsize=5.2, color=TRUSTED, zorder=3)
    arrow(ax, (0.25, 0.745), (0.31, 0.745))
    arrow(ax, (0.51, 0.745), (0.57, 0.745))
    arrow(ax, (0.75, 0.745), (0.76, 0.745))

    box(ax, (0.67, 0.38), 0.28, 0.13, "Admitted skill +\nproof obligations", face=CORRECTION_LIGHT, edge=CORRECTION, fontsize=5.5, weight="bold")
    arrow(ax, (0.86, 0.65), (0.82, 0.51), color=CORRECTION)
    ax.text(0.89, 0.57, "pass", ha="left", va="center", fontsize=5.1, color=CORRECTION, fontweight="bold")

    box(ax, (0.23, 0.36), 0.31, 0.16, "Retained witness\nremoves inconsistent\ncandidate", face=REGRESSION_LIGHT, edge=REGRESSION, fontsize=5.1)
    arrow(ax, (0.78, 0.67), (0.50, 0.51), color=REGRESSION, connection="arc3,rad=0.08")
    ax.text(0.62, 0.55, "fail", ha="center", va="center", fontsize=5.1, color=REGRESSION, fontweight="bold")
    arrow(ax, (0.25, 0.44), (0.14, 0.61), color=REGRESSION, connection="arc3,rad=-0.25")
    ax.text(0.11, 0.48, "smaller\nversion space", ha="center", va="center", fontsize=5.1, color=REGRESSION)

    box(ax, (0.27, 0.12), 0.23, 0.11, "Exhausted grammar\n→ no admission", face=LIGHT, edge=NEUTRAL, fontsize=5.2)
    arrow(ax, (0.39, 0.37), (0.39, 0.23), color=NEUTRAL)
    ax.text(0.97, 0.11, "Finite termination\nBalanced-witness contraction is conditional", ha="right", va="bottom", fontsize=5.1, color=CONDITIONAL)


def draw_execution(ax) -> None:
    setup_panel(ax, "Selective proof-carrying execution", "c")
    box(ax, (0.68, 0.89), 0.29, 0.075, "SOFTWARE + CONDITIONAL", face=CONDITIONAL_LIGHT, edge=CONDITIONAL, fontsize=5.0, weight="bold")

    box(ax, (0.03, 0.66), 0.17, 0.13, "Public input", face=LIGHT, edge=NEUTRAL, fontsize=5.5, weight="bold")
    diamond = Polygon([(0.32, 0.83), (0.44, 0.725), (0.32, 0.62), (0.20, 0.725)], closed=True,
                      facecolor=WHITE, edgecolor=TRUSTED, linewidth=0.9, zorder=2)
    ax.add_patch(diamond)
    ax.text(0.32, 0.725, "exactly one\npublic guard?", ha="center", va="center", fontsize=5.2, color=TRUSTED, zorder=3)
    arrow(ax, (0.20, 0.725), (0.21, 0.725))
    box(ax, (0.49, 0.66), 0.19, 0.13, "Typed extraction\n+ compilation", face=METHOD_LIGHT, edge=METHOD, fontsize=5.3, weight="bold")
    box(ax, (0.74, 0.66), 0.23, 0.13, "Semantic + exact\nresource admission", face=WHITE, edge=TRUSTED, fontsize=5.2, weight="bold")
    arrow(ax, (0.44, 0.725), (0.49, 0.725), color=METHOD)
    arrow(ax, (0.68, 0.725), (0.74, 0.725), color=METHOD)

    box(ax, (0.66, 0.36), 0.31, 0.14, "Pinned backend + projection\n→ recorded output", face=CORRECTION_LIGHT, edge=CORRECTION, fontsize=5.4, weight="bold")
    arrow(ax, (0.855, 0.66), (0.82, 0.50), color=CORRECTION)
    ax.text(0.88, 0.57, "admit", ha="left", va="center", fontsize=5.0, color=CORRECTION, fontweight="bold")

    box(ax, (0.08, 0.32), 0.42, 0.16, "Stored previous-library output\nbyte-identical fallback", face=LIGHT, edge=NEUTRAL, fontsize=5.5, weight="bold")
    arrow(ax, (0.27, 0.63), (0.23, 0.48), color=NEUTRAL)
    ax.text(0.15, 0.56, "zero / multiple", ha="center", va="center", fontsize=5.0, color=NEUTRAL)
    arrow(ax, (0.74, 0.68), (0.49, 0.45), color=REGRESSION, connection="arc3,rad=0.12")

    ax.text(0.03, 0.11, "Exact fallback outside unique coverage", ha="left", va="center", fontsize=5.2, color=TRUSTED, fontweight="bold")
    ax.text(0.97, 0.11, "Accepted-path correctness is conditional", ha="right", va="center", fontsize=5.2, color=CONDITIONAL, fontweight="bold")


def draw_promotion(ax) -> None:
    setup_panel(ax, "Independent promotion and immutable versioning", "d")
    tag(ax, 0.73, 0.89, "EMPIRICAL DECISION", CORRECTION, CORRECTION_LIGHT)

    ax.text(0.03, 0.82, "Full-denominator paired outcomes", ha="left", va="center", fontsize=5.7, fontweight="bold", color=TRUSTED)
    labels = [
        ("Correction", CORRECTION_LIGHT, CORRECTION),
        ("Regression", REGRESSION_LIGHT, REGRESSION),
        ("Both correct", METHOD_LIGHT, METHOD),
        ("Both wrong", LIGHT, NEUTRAL),
    ]
    for i, (label, face, edge) in enumerate(labels):
        x = 0.03 + 0.24 * i
        box(ax, (x, 0.66), 0.20, 0.105, label, face=face, edge=edge, fontsize=5.1, weight="bold")

    box(ax, (0.25, 0.40), 0.50, 0.17, "Fresh grouped promotion gate\ncorrections − regressions\nfrozen endpoint", face=WHITE, edge=TRUSTED, fontsize=5.2, weight="bold")
    for x in (0.13, 0.37, 0.61, 0.85):
        arrow(ax, (x, 0.66), (0.50, 0.57), color=TRUSTED, linewidth=0.6)

    box(ax, (0.55, 0.18), 0.40, 0.13, "PASS → append immutable L_(t+1)\ncontent-addressed successor", face=CORRECTION_LIGHT, edge=CORRECTION, fontsize=5.3, weight="bold")
    box(ax, (0.05, 0.18), 0.40, 0.13, "FAIL → retain L_t\nstate unchanged; witness retained", face=LIGHT, edge=NEUTRAL, fontsize=5.3, weight="bold")
    arrow(ax, (0.59, 0.40), (0.73, 0.31), color=CORRECTION)
    arrow(ax, (0.41, 0.40), (0.27, 0.31), color=NEUTRAL)

    ax.text(0.03, 0.08, "Prospective: prefix-code risk budget", ha="left", va="center", fontsize=5.1, color=CONDITIONAL, fontweight="bold")
    ax.text(0.97, 0.08, "Cumulative bound requires one fixed target", ha="right", va="center", fontsize=5.1, color=CONDITIONAL, fontweight="bold")


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(7.0866, 5.35), constrained_layout=False)
    fig.subplots_adjust(left=0.045, right=0.985, top=0.965, bottom=0.105, wspace=0.16, hspace=0.28)
    grid = fig.add_gridspec(2, 2, wspace=0.06, hspace=0.14)
    axes = {
        "a": fig.add_subplot(grid[0, 0]),
        "b": fig.add_subplot(grid[0, 1]),
        "c": fig.add_subplot(grid[1, 0]),
        "d": fig.add_subplot(grid[1, 1]),
    }
    draw_library(axes["a"])
    draw_construction(axes["b"])
    draw_execution(axes["c"])
    draw_promotion(axes["d"])

    fig.text(0.50, 0.505, "admitted artifact  →  selective execution  →  durable output", ha="center", va="center", fontsize=5.2, color=METHOD, fontweight="bold")
    fig.text(0.50, 0.030, "Finite grammar  ·  verifier-relative obligations  ·  exact fallback  ·  empirical benchmark utility", ha="center", va="bottom", fontsize=5.2, color=TRUSTED, fontweight="bold")
    fig.text(0.50, 0.010, "No universal natural-language proof  ·  no unrestricted recursive self-improvement", ha="center", va="bottom", fontsize=5.0, color=REGRESSION)

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
