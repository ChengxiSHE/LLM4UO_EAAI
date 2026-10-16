#!/usr/bin/env python3
"""Render Figure 3 from aggregate, body-free RetailOpt source data."""

from __future__ import annotations

import csv
import os
from pathlib import Path
import sys

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manuscript" / "source_data"
OUTPUT = ROOT / "manuscript" / "figures" / "figure3_retailopt_confirmation"

qa_scripts = os.environ.get("FIGURE_QA_SCRIPTS")
if not qa_scripts:
    raise RuntimeError("FIGURE_QA_SCRIPTS must point to the figure QA scripts")
sys.path.insert(0, qa_scripts)
from audit_panel_alignment import require_matplotlib_panel_alignment  # noqa: E402


BASE = "#73849A"
KNOWLEDGE = "#2468B4"
CORRECTION = "#43A047"
REGRESSION = "#C23B3B"
BOTH_WRONG = "#D7DCE2"
DARK = "#1F2933"
MUTED = "#5D6772"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "font.size": 6.5,
    "axes.titlesize": 7.2,
    "axes.labelsize": 6.5,
    "xtick.labelsize": 5.8,
    "ytick.labelsize": 6.2,
    "legend.fontsize": 5.7,
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 0.7,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
})


def read_rows(name: str) -> list[dict[str, str]]:
    with (SOURCE / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def panel_label(ax, label: str) -> None:
    ax.annotate(
        label,
        xy=(0, 1),
        xycoords="axes fraction",
        xytext=(-26, 7),
        textcoords="offset points",
        fontsize=8,
        fontweight="bold",
        ha="left",
        va="bottom",
        annotation_clip=False,
    )


def accuracy(
    ax,
    row: dict[str, str],
    *,
    title: str,
    subtitle: str,
    show_gain: bool = True,
) -> None:
    denominator = int(row["denominator"])
    values = [100 * int(row["base_correct"]) / denominator,
              100 * int(row["knowledge_correct"]) / denominator]
    bars = ax.barh([1, 0], values, height=0.58, color=[BASE, KNOWLEDGE])
    for bar, value in zip(bars, values):
        ax.text(value - 2.2, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%",
                ha="right", va="center", color="white", fontsize=6.2, fontweight="bold")
    if show_gain:
        ax.text(values[1] + 2, 0, f"+{values[1] - values[0]:.1f} pp",
                ha="left", va="center", color=CORRECTION, fontsize=6.1, fontweight="bold")
    ax.set_yticks([1, 0], ["Base", "Routed knowledge"])
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
    ax.set_xlabel("Full-denominator instance accuracy")
    ax.set_title(title, loc="left", fontweight="bold", pad=5)
    ax.text(0, 1.12, subtitle, transform=ax.transAxes, ha="left", va="bottom", fontsize=5.6, color=MUTED)


def paired(ax, row: dict[str, str]) -> None:
    keys = ["both_correct", "corrections", "regressions", "both_wrong"]
    names = ["Both correct", "Correction", "Regression", "Both wrong"]
    colors = [BASE, CORRECTION, REGRESSION, BOTH_WRONG]
    denominator = int(row["denominator"])
    left = 0.0
    for key, name, color in zip(keys, names, colors):
        count = int(row[key])
        width = 100 * count / denominator
        ax.barh(0, width, left=left, height=0.58, color=color, edgecolor="white", lw=0.6)
        if width >= 7:
            ax.text(left + width / 2, 0, str(count), ha="center", va="center",
                    fontsize=6.0, color="white" if color in (BASE, CORRECTION, REGRESSION) else DARK,
                    fontweight="bold")
        left += width
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.65, 0.80)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
    ax.set_xlabel("Paired archetype outcomes (n=38)")
    p_value = float(row["one_sided_exact_mcnemar_p"])
    ax.set_title("Primary paired evidence", loc="left", fontweight="bold", pad=5)
    ax.text(0.98, 0.91, f"25 corrections, 1 regression\nexact one-sided P={p_value:.2e}",
            transform=ax.transAxes, ha="right", va="top", fontsize=5.5, color=MUTED)
    ax.legend([Patch(facecolor=color) for color in colors], names, ncol=2,
              loc="lower center", bbox_to_anchor=(0.5, -0.52),
              columnspacing=0.8, handlelength=1.0, handletextpad=0.5)


def robustness(ax, row: dict[str, str]) -> None:
    accuracy(ax, row, title="Label-blind robustness",
             subtitle="Post hoc, same benchmark; 27 corrections and 0 regressions",
             show_gain=False)


def diagnostics(ax, rows: list[dict[str, str]]) -> None:
    labels = [row["diagnostic"] for row in rows]
    y = [1, 0]
    height = 0.28
    for yi, row in zip(y, rows):
        denominator = int(row["denominator"])
        base = 100 * int(row["base_correct"]) / denominator
        knowledge = 100 * int(row["knowledge_correct"]) / denominator
        ax.barh(yi + height / 2, base, height=height, color=BASE)
        ax.barh(yi - height / 2, knowledge, height=height, color=KNOWLEDGE)
        ax.text(base + 1.5, yi + height / 2, f"{int(row['base_correct'])}/{denominator}",
                ha="left", va="center", fontsize=5.6, color=BASE)
        ax.text(knowledge - 1.5, yi - height / 2, f"{int(row['knowledge_correct'])}/{denominator}",
                ha="right", va="center", fontsize=5.6, color="white", fontweight="bold")
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
    ax.set_xlabel("Fully correct routed decisions")
    ax.set_ylim(-0.55, 1.55)
    ax.set_title("Post hoc error localization", loc="left", fontweight="bold", pad=5)
    ax.legend([Patch(facecolor=BASE), Patch(facecolor=KNOWLEDGE)], ["Base", "Routed knowledge"],
              loc="lower center", bbox_to_anchor=(0.5, -0.48), ncol=2,
              columnspacing=0.9, handlelength=1.0, handletextpad=0.5)


def main() -> None:
    summary = read_rows("figure3_retailopt_summary.csv")
    diagnostics_rows = read_rows("figure3_retailopt_diagnostics.csv")
    primary_instance = next(row for row in summary if row["study"] == "prospective_primary" and row["unit"] == "instance")
    primary_archetype = next(row for row in summary if row["study"] == "prospective_primary" and row["unit"] == "archetype")
    blind_instance = next(row for row in summary if row["study"] == "posthoc_label_blind" and row["unit"] == "instance")
    blind_archetype = next(row for row in summary if row["study"] == "posthoc_label_blind" and row["unit"] == "archetype")
    assert (int(primary_instance["base_correct"]), int(primary_instance["knowledge_correct"])) == (50, 170)
    assert (int(primary_archetype["corrections"]), int(primary_archetype["regressions"])) == (25, 1)
    assert (int(blind_instance["base_correct"]), int(blind_instance["knowledge_correct"])) == (50, 185)
    assert (int(blind_archetype["corrections"]), int(blind_archetype["regressions"])) == (27, 0)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(7.0866, 4.3307), constrained_layout=True)
    grid = fig.add_gridspec(2, 3, width_ratios=[1.15, 1.15, 1.0], height_ratios=[1, 1])
    axes = {
        "a": fig.add_subplot(grid[0, :2]),
        "b": fig.add_subplot(grid[0, 2]),
        "c": fig.add_subplot(grid[1, :2]),
        "d": fig.add_subplot(grid[1, 2]),
    }
    accuracy(axes["a"], primary_instance, title="Prospective independent-source accuracy",
             subtitle="RetailOpt-190; 38 archetypes x 5 variants")
    paired(axes["b"], primary_archetype)
    robustness(axes["c"], blind_instance)
    diagnostics(axes["d"], diagnostics_rows)
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
