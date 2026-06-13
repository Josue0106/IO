from __future__ import annotations

from typing import Dict
import math
import textwrap
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

from core.data_model import Area, Relation
from core.layout_metrics import Rect


def plot_layout(layout: Dict[str, Rect], facility_width: int, facility_height: int, title: str):
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_title(title)
    ax.set_xlim(0, facility_width)
    ax.set_ylim(0, facility_height)
    ax.set_aspect("equal")

    palette = plt.cm.tab20.colors
    for idx, (code, rect) in enumerate(layout.items()):
        patch = Rectangle((rect.x, rect.y), rect.w, rect.h, facecolor=palette[idx % len(palette)], alpha=0.18, linewidth=2)
        ax.add_patch(patch)
        label = textwrap.fill(f"{code}\n{rect.w}×{rect.h} m", width=18)
        ax.text(rect.x + rect.w / 2.0, rect.y + rect.h / 2.0, label, ha="center", va="center", fontsize=9)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.4)
    return fig


def plot_relation_graph(areas: list[Area], relations: list[Relation]):
    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    ax.set_title("Diagrama de relaciones")
    ax.axis("off")

    radius = 1.0
    positions = {}
    total = len(areas)
    for idx, area in enumerate(areas):
        angle = 2.0 * math.pi * idx / max(total, 1)
        positions[area.code] = (radius * math.cos(angle), radius * math.sin(angle))

    styles = {
        "A": {"color": "#c62828", "linewidth": 4.5, "linestyle": "-", "alpha": 0.95},
        "E": {"color": "#ef6c00", "linewidth": 3.5, "linestyle": "-", "alpha": 0.9},
        "I": {"color": "#f9a825", "linewidth": 2.5, "linestyle": "-", "alpha": 0.85},
        "O": {"color": "#6d4c41", "linewidth": 1.8, "linestyle": ":", "alpha": 0.8},
        "U": {"color": "#9e9e9e", "linewidth": 1.0, "linestyle": ":", "alpha": 0.55},
        "X": {"color": "#1565c0", "linewidth": 2.5, "linestyle": "--", "alpha": 0.95},
    }

    for rel in relations:
        if rel.a not in positions or rel.b not in positions or rel.a == rel.b:
            continue
        x_values = [positions[rel.a][0], positions[rel.b][0]]
        y_values = [positions[rel.a][1], positions[rel.b][1]]
        style = styles.get(rel.rel, styles["U"])
        ax.plot(x_values, y_values, **style, zorder=1)

    for area in areas:
        x, y = positions[area.code]
        ax.scatter([x], [y], s=650, color="#263238", zorder=3)
        ax.scatter([x], [y], s=420, color="#eceff1", zorder=4)
        label = textwrap.fill(f"{area.code}\n{area.name}", width=16)
        ax.text(x, y, label, ha="center", va="center", fontsize=8.5, zorder=5)

    legend_handles = [
        Line2D([0], [0], color=style["color"], lw=style["linewidth"], linestyle=style["linestyle"], label=rel)
        for rel, style in [("A", styles["A"]), ("E", styles["E"]), ("I", styles["I"]), ("O", styles["O"]), ("U", styles["U"]), ("X", styles["X"])]
    ]
    ax.legend(handles=legend_handles, loc="lower center", ncol=3, frameon=False)
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    return fig
