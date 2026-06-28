# core/reporting.py
"""
Reporting utilities (plots + AIMS table rendering) extracted from your PE_gui logic,
refactored for Streamlit/headless usage.

Main entrypoint:
    build_reports(baby_age_months, baby_score, scores, out_dir) -> dict(paths)

Assumptions:
- `scores` is either:
    A) a dataclass with attributes: prone, supine, sitting, standing (lists of bool)
       and optionally .total()
  OR
    B) a dict with keys: "prone","supine","sitting","standing" (lists of bool)

- Your config.py contains FIXED_RESOLUTION, and optionally other constants.
"""

from __future__ import annotations

from dataclasses import is_dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt


# ---------- Utilities ----------

def _as_bool_list(x: Any) -> List[bool]:
    if x is None:
        return []
    if isinstance(x, list):
        return [bool(v) for v in x]
    return list(x)


def _scores_to_lists(scores: Any) -> Tuple[List[bool], List[bool], List[bool], List[bool]]:
    """
    Supports:
      - dataclass/obj: scores.prone / scores.supine / scores.sitting / scores.standing
      - dict: scores["prone"] ...
      - tuple/list of 4 lists: (prone, supine, sitting, standing)
    """
    if isinstance(scores, (tuple, list)) and len(scores) == 4:
        return tuple(_as_bool_list(s) for s in scores)  # type: ignore

    if isinstance(scores, dict):
        return (
            _as_bool_list(scores.get("prone")),
            _as_bool_list(scores.get("supine")),
            _as_bool_list(scores.get("sitting")),
            _as_bool_list(scores.get("standing")),
        )

    # dataclass or simple object
    if is_dataclass(scores) or hasattr(scores, "__dict__"):
        return (
            _as_bool_list(getattr(scores, "prone", None)),
            _as_bool_list(getattr(scores, "supine", None)),
            _as_bool_list(getattr(scores, "sitting", None)),
            _as_bool_list(getattr(scores, "standing", None)),
        )

    raise TypeError("Unsupported scores type. Provide dict/dataclass/tuple-of-4.")


def to_str_list(bool_list: List[bool]) -> List[str]:
    return ["1" if v else "0" for v in bool_list]


def create_curve(x_points: List[float], y_points: List[float], months: np.ndarray) -> np.ndarray:
    return np.interp(months, x_points, y_points)


def default_aims_curves(months: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Curves copied from your PE_gui (piecewise-linear interpolation).
    """
    p90 = create_curve([0.2, 2.5, 3.5, 5.5, 6], [4, 12, 14, 26, 26.5], months)
    p75 = create_curve([0.5, 1.3, 2.5, 3.5, 5.5, 6], [4, 7, 11, 13, 24, 25], months)
    p50 = create_curve([0.6, 3.2, 6], [4, 12, 22], months)
    p25 = create_curve([0.6, 3.5, 4.5, 5.5, 6], [4, 12, 13, 20, 21.5], months)
    p10 = create_curve([0.6, 1.5, 3.4, 4.5, 5.5, 6], [4, 5, 11, 12, 19, 20.25], months)
    p5  = create_curve([0.6, 1.5, 3.4, 4.5, 5.5, 6], [4, 5, 9, 10, 19, 20.25], months)
    return {"p90": p90, "p75": p75, "p50": p50, "p25": p25, "p10": p10, "p5": p5}


# ---------- Angles plot ----------

def plot_angle_changes_over_time(
    angles_tsv_path: str | Path,
    save_path: str | Path,
) -> Path:
    """
    Creates 3 stacked plots (Neck, Elbow, Knee) over frames.
    Headless-safe: saves to file and closes figure.
    """
    angles_tsv_path = Path(angles_tsv_path)
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(angles_tsv_path, delimiter="\t")

    fig = plt.figure(figsize=(12, 6))
    gs = matplotlib.gridspec.GridSpec(3, 1, height_ratios=[1, 1, 1])

    ax1 = fig.add_subplot(gs[0])
    if "R_Eye-Ear-Vertical" in df.columns:
        ax1.plot(df["Frame"], df["R_Eye-Ear-Vertical"], label="R_Eye-Ear-Vertical")
    ax1.set_title("Change of Neck Angle Over Time")
    ax1.set_xlabel("Frame")
    ax1.set_ylabel("Angle (°)")
    ax1.grid(True)
    ax1.legend(loc="best")

    ax2 = fig.add_subplot(gs[1])
    if "R_Wrist-Elbow-Shoulder" in df.columns:
        ax2.plot(df["Frame"], df["R_Wrist-Elbow-Shoulder"], label="R_Wrist-Elbow-Shoulder")
    ax2.set_title("Change of Elbow Angle Over Time")
    ax2.set_xlabel("Frame")
    ax2.set_ylabel("Angle (°)")
    ax2.grid(True)
    ax2.legend(loc="best")

    ax3 = fig.add_subplot(gs[2])
    if "R_Hip-Knee-Ankle" in df.columns:
        ax3.plot(df["Frame"], df["R_Hip-Knee-Ankle"], label="R_Hip-Knee-Ankle")
    ax3.set_title("Change of Knee Angle Over Time")
    ax3.set_xlabel("Frame")
    ax3.set_ylabel("Angle (°)")
    ax3.grid(True)
    ax3.legend(loc="best")

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


# ---------- AIMS report mapping ----------

def generate_aims_report(scores: Any) -> Dict[str, List[Tuple[str, str]]]:
    """
    Takes scores and maps them to AIMS items.
    Returns dict:
      { "Prone": [(label, "0/1"), ...], ... }
    """
    prone_b, supine_b, sitting_b, standing_b = _scores_to_lists(scores)

    prone   = to_str_list(prone_b)
    supine  = to_str_list(supine_b)
    sitting = to_str_list(sitting_b)
    standing= to_str_list(standing_b)

    # Keep your original labels/order
    return {
        "Prone": [
            ("Prone lying 1", prone[0] if len(prone) > 0 else "0"),
            ("Prone lying 2", prone[1] if len(prone) > 1 else "0"),
            ("Prone prop", prone[2] if len(prone) > 2 else "0"),
            ("Forearm support 1", prone[3] if len(prone) > 3 else "0"),
            ("Prone mobility", prone[4] if len(prone) > 4 else "0"),
            ("Forearm support 2", prone[5] if len(prone) > 5 else "0"),
            ("Extended arm support", prone[6] if len(prone) > 6 else "0"),
            ("Rolling prone to supine without rotation", prone[7] if len(prone) > 7 else "0"),
            ("Swimming", prone[8] if len(prone) > 8 else "0"),
            ("Reaching from forearm support", prone[9] if len(prone) > 9 else "0"),
            ("Pivoting", prone[10] if len(prone) > 10 else "0"),
        ],
        "Supine": [
            ("Supine lying 1", supine[0] if len(supine) > 0 else "0"),
            ("Supine lying 2", supine[1] if len(supine) > 1 else "0"),
            ("Supine lying 3", supine[2] if len(supine) > 2 else "0"),
            ("Supine lying 4", supine[3] if len(supine) > 3 else "0"),
            ("Hands to knees", supine[4] if len(supine) > 4 else "0"),
            ("Active extension", supine[5] if len(supine) > 5 else "0"),
            ("Hands to feet", supine[6] if len(supine) > 6 else "0"),
            ("Rotating supine to prone without rotation", supine[7] if len(supine) > 7 else "0"),
        ],
        "Sitting": [
            ("Sitting with support", sitting[0] if len(sitting) > 0 else "0"),
            ("Sitting with propped arms", sitting[1] if len(sitting) > 1 else "0"),
            ("Pull to sit", sitting[2] if len(sitting) > 2 else "0"),
            ("Unsustained sitting", sitting[3] if len(sitting) > 3 else "0"),
            ("Sitting with arm support", sitting[4] if len(sitting) > 4 else "0"),
            ("Unsustained sitting without arm support", sitting[5] if len(sitting) > 5 else "0"),
            ("Weight shift in unsustained sitting", sitting[6] if len(sitting) > 6 else "0"),
        ],
        "Standing": [
            ("Support standing 1", standing[0] if len(standing) > 0 else "0"),
            ("Support standing 2", standing[1] if len(standing) > 1 else "0"),
            ("Support standing 3", standing[2] if len(standing) > 2 else "0"),
        ],
    }


# ---------- AIMS report plot (curve + table) ----------

def _color_aims_score_cells(table):
    """
    Colors the score cells in the AIMS table:
    - Green for score 1
    - Red for score 0
    """
    for (row_idx, col_idx), cell in table.get_celld().items():
        if row_idx == 0:
            cell.set_fontsize(10)
            cell.set_text_props(weight="bold")
            continue

        text = cell.get_text().get_text()
        if "(" in text and ")" in text:
            score_str = text.split("(")[-1].split(")")[0].strip()
            if score_str == "1":
                cell.get_text().set_color("green")
            elif score_str == "0":
                cell.get_text().set_color("red")


def plot_aims_report(
    months: np.ndarray,
    curves: Dict[str, np.ndarray],
    baby_age_months: float,
    baby_score: int,
    report_data: Dict[str, List[Tuple[str, str]]],
    save_path: str | Path,
) -> Path:
    """
    Creates a figure:
      - AIMS percentile curves + infant point
      - Title row
      - AIMS table with colored 0/1
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(12, 13))
    gs = matplotlib.gridspec.GridSpec(3, 1, height_ratios=[4, 0.3, 1])

    # --- Plot curves
    ax0 = fig.add_subplot(gs[0])
    ax0.plot(months, curves["p90"], label="90th %ile")
    ax0.plot(months, curves["p75"], label="75th %ile")
    ax0.plot(months, curves["p50"], label="50th %ile")
    ax0.plot(months, curves["p25"], label="25th %ile")
    ax0.plot(months, curves["p10"], label="10th %ile")
    ax0.plot(months, curves["p5"],  label="5th %ile")

    ax0.scatter(
        baby_age_months, baby_score, s=40,
        label=f"Infant: {baby_age_months} months, Score: {baby_score}",
        color="black",
        zorder=5
    )
    ax0.axhline(y=4, color="gray", linewidth=1)

    ax0.set_xlim(0, 6)
    ax0.set_ylim(0, 30)
    ax0.set_xticks(np.arange(0, 7, 1))
    ax0.set_yticks(np.arange(0, 28, 2))
    ax0.set_xlabel("Age (months)")
    ax0.set_ylabel("AIMS Score")
    ax0.set_title("AIMS Score vs Age - Infant Development Position")
    ax0.grid(True)
    ax0.legend(loc="best")

    # --- Title Row
    ax_title = fig.add_subplot(gs[1])
    ax_title.axis("off")
    ax_title.text(0.5, 0.5, "AIMS Report", ha="center", va="center", fontsize=14, fontweight="bold")

    # --- Table Row
    ax1 = fig.add_subplot(gs[2])
    ax1.axis("off")

    max_rows = max(len(v) for v in report_data.values())
    columns = list(report_data.keys())
    table_data = []

    for i in range(max_rows):
        row = []
        for col in columns:
            if i < len(report_data[col]):
                label, score = report_data[col][i]
                row.append(f"{label} ({score})")
            else:
                row.append("")
        table_data.append(row)

    table = ax1.table(cellText=table_data, colLabels=columns, loc="center", cellLoc="left")
    table.scale(1, 2.5)
    table.auto_set_font_size(False)
    table.set_fontsize(9)

    _color_aims_score_cells(table)

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


# ---------- Percentile bar (parent side) ----------

def plot_aims_percentile_bar(
    baby_age_months: float,
    baby_score: int,
    curves: Dict[str, np.ndarray],
    save_path: str | Path,
) -> Path:
    """
    Creates the percentile bar + arrow marker + explanation text (like in your GUI).
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    months = np.linspace(0, 6, 100)
    age_index = int(np.abs(months - baby_age_months).argmin())

    cutoffs = {
        "5th":  float(curves["p5"][age_index]),
        "10th": float(curves["p10"][age_index]),
        "25th": float(curves["p25"][age_index]),
        "50th": float(curves["p50"][age_index]),
        "75th": float(curves["p75"][age_index]),
        "90th": float(curves["p90"][age_index]),
    }

    # Boundaries copied from your script (kept same labels & colors)
    boundaries = [
        (4, cutoffs["5th"], '<5th', 'red'),
        (cutoffs["5th"], cutoffs["10th"], '5–10th', 'orangered'),
        (cutoffs["10th"], cutoffs["25th"], '10–25th', 'gold'),
        (cutoffs["25th"], cutoffs["50th"], '25–50th', 'yellowgreen'),
        (cutoffs["50th"], cutoffs["75th"], '50–75th', 'mediumseagreen'),
        (cutoffs["75th"], cutoffs["90th"], '75–90th', 'forestgreen'),
        (cutoffs["90th"], cutoffs["90th"] + 3, '>90th', 'darkgreen'),
    ]

    explanations = {
        '<5th': "This indicates significantly delayed motor development for this age.",
        '5–10th': "Motor development is below average; monitoring is advised.",
        '10–25th': "Motor skills are slightly below average; some delay may be present.",
        '25–50th': "Motor development is in the average range.",
        '50–75th': "The infant shows above-average motor development.",
        '75–90th': "Motor skills are well-developed for age.",
        '>90th': "The infant demonstrates advanced motor development for this age."
    }

    percentile_range = "Unknown"
    for start, end, label, _ in boundaries:
        if start <= baby_score < end:
            percentile_range = label
            break
    if baby_score >= cutoffs["90th"]:
        percentile_range = ">90th"
    elif baby_score < cutoffs["5th"]:
        percentile_range = "<5th"

    fig = plt.figure(figsize=(12, 3.5), dpi=100)
    ax = fig.add_axes([0.05, 0.4, 0.9, 0.45])

    for start, end, label, color in boundaries:
        ax.axvspan(start, end, color=color)
        ax.text((start + end) / 2, 0.85, label, ha="center", va="center",
                color="black", fontsize=10, fontweight="bold")

    # Arrow marker
    ax.plot(baby_score, -0.2, marker="^", color="black", markersize=18)

    xmin = 4
    xmax = int(cutoffs["90th"] + 3)
    for x in range(xmin, xmax + 1):
        ax.axvline(x, color="white", linestyle="--", linewidth=0.8, alpha=0.3)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(-0.4, 1.1)
    ax.set_xticks(range(xmin, xmax + 1))
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=9)
    ax.set_xlabel("AIMS Score")

    ax.set_title(f"AIMS Score Percentile Range at {round(baby_age_months, 2)} Months", pad=10)
    fig.text(0.5, 0.08, f'The infant is in the "{percentile_range}" percentile',
             ha="center", va="center", fontsize=10, fontweight="bold")
    fig.text(0.5, 0.02, f"Explanation: {explanations.get(percentile_range, 'No explanation available.')}",
             ha="center", va="center", fontsize=10, style="italic")

    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


def plot_supine_parameters_table(
    parameters_status: Dict[str, bool],
    task_status: List[bool],
    save_path: str | Path,
) -> Path:
    """
    Creates a table image for the 9 Supine tasks:
    - 9 rows
    - Parameter values - green if happened (True), red if not (False)
    - Task names - green if all parameters in their list are True, red if not
    - Parameters list for each task
    - Age range for each task as a list [Min, Max]
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    task_info = [
        ("1. Supine Lying 1", "[0,2]", []),
        ("2. Supine Lying 2", "[0,2]", []),
        ("3. Supine Lying 3", "[2,3]", ["Head in Midline"]),
        ("4. Supine Lying 4", "[2,4]", ["Head in Midline", "Chin Tuck", "Hands to Chest"]),
        ("5. Hands to Knees", "[2,5]", ["Head in Midline", "Chin Tuck", "Hands to Knees"]),
        ("6. Active Extension", "[3,6]", ["Neck Hyperextension", "Leg Extension"]),
        ("7. Hands to Feet", "[4,6]", ["Head in Midline", "Chin Tuck", "Hands to Feet"]),
        ("8. Rolling (no rotation)", "[4,9]", ["Rolled Sideways", "No Segmental Rotation"]),
        ("9. Rolling (with rotation)", "[6,9]", ["Rolled Sideways", "Segmental Rotation"])
    ]

    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=150)
    ax.axis("off")

    y_start = 0.95
    y_step = 0.085

    # Header row
    ax.text(0.02, y_start, "Task Name", fontweight="bold", fontsize=11, color="#2c3e50")
    ax.text(0.38, y_start, "Age Range", fontweight="bold", fontsize=11, color="#2c3e50")
    ax.text(0.55, y_start, "Parameters Checked", fontweight="bold", fontsize=11, color="#2c3e50")

    # Draw a line under header
    ax.plot([0.02, 0.98], [y_start - 0.02, y_start - 0.02], color="#bdc3c7", linewidth=1.5)

    for i, (name, age, param_keys) in enumerate(task_info):
        y = y_start - 0.05 - (i * y_step)

        # Task passes if index in task_status is True (or if no parameters are checked, which are baseline)
        is_passed = task_status[i] if i < len(task_status) else False
        task_color = "green" if is_passed else "red"

        # Draw task name
        ax.text(0.02, y, name, fontweight="semibold", fontsize=10, color=task_color)

        # Draw age range
        ax.text(0.38, y, age, fontsize=10, color="#7f8c8d")

        # Draw parameters list
        if not param_keys:
            ax.text(0.55, y, "Baseline (Passed)", fontsize=10, color="green", style="italic")
        else:
            x_offset = 0.55
            for idx, pk in enumerate(param_keys):
                status = parameters_status.get(pk, False)
                p_color = "green" if status else "red"
                text_str = pk
                if idx < len(param_keys) - 1:
                    text_str += ", "

                ax.text(x_offset, y, text_str, fontsize=9.5, color=p_color, fontweight="medium")
                x_offset += len(text_str) * 0.0072

        # Draw separator line
        ax.plot([0.02, 0.98], [y - 0.025, y - 0.025], color="#ecf0f1", linewidth=0.8)

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


# ---------- High-level helper used by pipeline ----------

def build_reports(
    baby_age_months: float,
    baby_score: int,
    scores: Any,
    out_dir: str | Path,
    angles_tsv_path: Optional[str | Path] = None,
    months_grid: Optional[np.ndarray] = None,
) -> Dict[str, str]:
    """
    Generates all report images and returns file paths.

    Parameters:
      - baby_age_months, baby_score: scalars
      - scores: your AIMS boolean lists (dataclass/dict/tuple)
      - out_dir: folder to write outputs
      - angles_tsv_path: if provided, will also generate angles plot
      - months_grid: override default np.linspace(0,6,100)

    Returns:
      {
        "angles_plot": "...jpg"  (only if angles_tsv_path provided)
        "expert_plot": "...jpg",
        "parent_plot": "...jpg",
      }
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    months = months_grid if months_grid is not None else np.linspace(0, 6, 100)
    curves = default_aims_curves(months)
    report_data = generate_aims_report(scores)

    expert_plot = out_dir / "Expert_Side_Report.jpg"
    parent_plot = out_dir / "Parent_Side_Report.jpg"

    plot_aims_report(
        months=months,
        curves=curves,
        baby_age_months=baby_age_months,
        baby_score=baby_score,
        report_data=report_data,
        save_path=expert_plot,
    )

    plot_aims_percentile_bar(
        baby_age_months=baby_age_months,
        baby_score=baby_score,
        curves=curves,
        save_path=parent_plot,
    )

    result = {
        "expert_plot": str(expert_plot),
        "parent_plot": str(parent_plot),
    }

    # Check if we should plot the supine parameters table
    supine_params = getattr(scores, "supine_parameters", None)
    if supine_params is not None:
        table_img_path = out_dir / "Supine_Parameters_Table.jpg"
        plot_supine_parameters_table(supine_params, scores.supine, table_img_path)
        result["supine_table"] = str(table_img_path)

    if angles_tsv_path is not None:
        angles_plot = out_dir / "Angles_Graph.jpg"
        plot_angle_changes_over_time(angles_tsv_path, angles_plot)
        result["angles_plot"] = str(angles_plot)

    return result
