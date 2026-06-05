from __future__ import annotations

from typing import Dict
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from core.layout_metrics import Rect


def plot_layout(layout: Dict[str, Rect], facility_width: int, facility_height: int, title: str):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.set_title(title)
    ax.set_xlim(0, facility_width)
    ax.set_ylim(0, facility_height)
    ax.set_aspect("equal")

    for code, rect in layout.items():
        patch = Rectangle((rect.x, rect.y), rect.w, rect.h, fill=False, linewidth=2)
        ax.add_patch(patch)
        ax.text(rect.x + rect.w / 2.0, rect.y + rect.h / 2.0, code, ha="center", va="center")

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.4)
    return fig
