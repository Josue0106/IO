from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math
import time

from core.data_model import Area, CaseData
from core.layout_metrics import Rect, manhattan_center_distance
from core.matrices import relation_score


@dataclass(frozen=True)
class LayoutResult:
    layout: Dict[str, Rect]
    runtime_s: float


def _dimension_candidates(min_area: int, max_w: int, max_h: int) -> List[Tuple[int, int]]:
    candidates: List[Tuple[int, int]] = []
    for w in range(1, max_w + 1):
        for h in range(1, max_h + 1):
            if w * h >= min_area:
                candidates.append((w, h))
    candidates.sort(key=lambda wh: (wh[0] * wh[1], abs(wh[0] - wh[1])))
    return candidates


def _choose_dimensions(min_area: int, max_w: int, max_h: int) -> Tuple[int, int]:
    candidates = _dimension_candidates(min_area, max_w, max_h)
    return candidates[0]


def _fits(layout: Dict[str, Rect], x: int, y: int, w: int, h: int) -> bool:
    for rect in layout.values():
        if not (x + w <= rect.x or rect.x + rect.w <= x or y + h <= rect.y or rect.y + rect.h <= y):
            return False
    return True


def slp_layout(case: CaseData, score_df) -> LayoutResult:
    start = time.perf_counter()
    facility = case.facility

    area_scores = relation_score(case.areas, score_df)
    ordered = sorted(case.areas, key=lambda a: area_scores[a.code], reverse=True)

    layout: Dict[str, Rect] = {}

    for idx, area in enumerate(ordered):
        required_area = int(math.ceil(area.min_area * (1.0 + case.growth_percent)))
        w, h = _choose_dimensions(required_area, facility.width, facility.height)

        if idx == 0:
            x = max(0, (facility.width - w) // 2)
            y = max(0, (facility.height - h) // 2)
            layout[area.code] = Rect(x=x, y=y, w=w, h=h)
            continue

        best_score = None
        best_rect = None

        for x in range(0, facility.width - w + 1):
            for y in range(0, facility.height - h + 1):
                if not _fits(layout, x, y, w, h):
                    continue

                candidate = Rect(x=x, y=y, w=w, h=h)
                score = 0.0
                for other_code, other_rect in layout.items():
                    weight = int(score_df.loc[area.code, other_code])
                    dist = manhattan_center_distance(candidate, other_rect)
                    score += weight / (1.0 + dist)

                for a_code, b_code in case.constraints.must_adjacent:
                    if area.code not in {a_code, b_code}:
                        continue
                    other = b_code if area.code == a_code else a_code
                    if other in layout:
                        dist = manhattan_center_distance(candidate, layout[other])
                        score += 5.0 / (1.0 + dist)

                for a_code, b_code in case.constraints.must_separate:
                    if area.code not in {a_code, b_code}:
                        continue
                    other = b_code if area.code == a_code else a_code
                    if other in layout:
                        dist = manhattan_center_distance(candidate, layout[other])
                        score -= 5.0 / (1.0 + dist)

                if best_score is None or score > best_score:
                    best_score = score
                    best_rect = candidate

        if best_rect is None:
            raise RuntimeError("No feasible position for area")
        layout[area.code] = best_rect

    runtime_s = time.perf_counter() - start
    return LayoutResult(layout=layout, runtime_s=runtime_s)
