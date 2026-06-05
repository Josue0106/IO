from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .data_model import Area, Flow, Relation


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int


def center_x2(rect: Rect) -> int:
    return 2 * rect.x + rect.w


def center_y2(rect: Rect) -> int:
    return 2 * rect.y + rect.h


def manhattan_center_distance(rect_a: Rect, rect_b: Rect) -> int:
    return abs(center_x2(rect_a) - center_x2(rect_b)) + abs(center_y2(rect_a) - center_y2(rect_b))


def is_adjacent(rect_a: Rect, rect_b: Rect) -> bool:
    horizontal_touch = rect_a.x + rect_a.w == rect_b.x or rect_b.x + rect_b.w == rect_a.x
    vertical_overlap = not (rect_a.y + rect_a.h <= rect_b.y or rect_b.y + rect_b.h <= rect_a.y)

    vertical_touch = rect_a.y + rect_a.h == rect_b.y or rect_b.y + rect_b.h == rect_a.y
    horizontal_overlap = not (rect_a.x + rect_a.w <= rect_b.x or rect_b.x + rect_b.w <= rect_a.x)

    return (horizontal_touch and vertical_overlap) or (vertical_touch and horizontal_overlap)


def compute_metrics(
    layout: Dict[str, Rect],
    flows: List[Flow],
    relations: List[Relation],
    facility_area: int,
) -> Dict[str, float]:
    total_flow_distance = 0
    for flow in flows:
        rect_a = layout[flow.origin]
        rect_b = layout[flow.dest]
        dist = manhattan_center_distance(rect_a, rect_b)
        total_flow_distance += flow.value * dist

    ae_satisfied = 0
    x_violations = 0
    for rel in relations:
        if rel.a not in layout or rel.b not in layout:
            continue
        rect_a = layout[rel.a]
        rect_b = layout[rel.b]
        adjacent = is_adjacent(rect_a, rect_b)
        if rel.rel in {"A", "E"} and adjacent:
            ae_satisfied += 1
        if rel.rel == "X" and adjacent:
            x_violations += 1

    used_area = sum(rect.w * rect.h for rect in layout.values())

    xs = [rect.x for rect in layout.values()]
    ys = [rect.y for rect in layout.values()]
    xe = [rect.x + rect.w for rect in layout.values()]
    ye = [rect.y + rect.h for rect in layout.values()]
    if xs and ys:
        bbox_area = (max(xe) - min(xs)) * (max(ye) - min(ys))
    else:
        bbox_area = 0

    aspect_ratios = []
    for rect in layout.values():
        if rect.h == 0 or rect.w == 0:
            continue
        aspect_ratios.append(max(rect.w / rect.h, rect.h / rect.w))
    avg_aspect_ratio = sum(aspect_ratios) / len(aspect_ratios) if aspect_ratios else 0.0

    return {
        "flow_distance": float(total_flow_distance),
        "ae_satisfied": float(ae_satisfied),
        "x_violations": float(x_violations),
        "area_utilization": float(used_area) / float(facility_area),
        "compactness": float(used_area) / float(bbox_area) if bbox_area else 0.0,
        "avg_aspect_ratio": float(avg_aspect_ratio),
    }
