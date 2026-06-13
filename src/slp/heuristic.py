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
    status: str = "feasible"
    a_hard_violations: int = 0


def _dimension_candidates(min_area: int, max_w: int, max_h: int) -> List[Tuple[int, int]]:
    candidates: List[Tuple[int, int]] = []
    for w in range(1, max_w + 1):
        for h in range(1, max_h + 1):
            if w * h >= min_area:
                candidates.append((w, h))
    candidates.sort(key=lambda wh: (wh[0] * wh[1], abs(wh[0] - wh[1])))
    return candidates


def _adjacent(rect_a: Rect, rect_b: Rect) -> bool:
    horizontal_touch = rect_a.x + rect_a.w == rect_b.x or rect_b.x + rect_b.w == rect_a.x
    vertical_overlap = not (rect_a.y + rect_a.h <= rect_b.y or rect_b.y + rect_b.h <= rect_a.y)

    vertical_touch = rect_a.y + rect_a.h == rect_b.y or rect_b.y + rect_b.h == rect_a.y
    horizontal_overlap = not (rect_a.x + rect_a.w <= rect_b.x or rect_b.x + rect_b.w <= rect_a.x)

    return (horizontal_touch and vertical_overlap) or (vertical_touch and horizontal_overlap)


def _count_hard_violations(layout: Dict[str, Rect], must_adjacent: List[Tuple[str, str]], must_separate: List[Tuple[str, str]]) -> int:
    violations = 0
    for a_code, b_code in must_adjacent:
        if a_code in layout and b_code in layout and not _adjacent(layout[a_code], layout[b_code]):
            violations += 1
    for a_code, b_code in must_separate:
        if a_code in layout and b_code in layout and _adjacent(layout[a_code], layout[b_code]):
            violations += 1
    return violations


def _seed_positions(facility_width: int, facility_height: int, w: int, h: int) -> List[Tuple[int, int]]:
    center = (max(0, (facility_width - w) // 2), max(0, (facility_height - h) // 2))
    corners = [
        (0, 0),
        (max(0, facility_width - w), 0),
        (0, max(0, facility_height - h)),
        (max(0, facility_width - w), max(0, facility_height - h)),
    ]
    return [center] + corners


def _contains(outer: Rect, inner: Rect) -> bool:
    return (
        outer.x <= inner.x
        and outer.y <= inner.y
        and outer.x + outer.w >= inner.x + inner.w
        and outer.y + outer.h >= inner.y + inner.h
    )


def _prune_free_rects(free_rects: List[Rect]) -> List[Rect]:
    cleaned = [rect for rect in free_rects if rect.w > 0 and rect.h > 0]
    cleaned.sort(key=lambda rect: (rect.w * rect.h, rect.x, rect.y), reverse=True)
    pruned: List[Rect] = []
    for rect in cleaned:
        if any(_contains(existing, rect) for existing in pruned):
            continue
        pruned = [existing for existing in pruned if not _contains(rect, existing)]
        pruned.append(rect)
    pruned.sort(key=lambda rect: (rect.y, rect.x, -rect.w * rect.h))
    return pruned


def _candidate_positions_in_rect(free_rect: Rect, w: int, h: int) -> List[Tuple[int, int]]:
    candidates = [
        (free_rect.x, free_rect.y),
        (free_rect.x + free_rect.w - w, free_rect.y),
        (free_rect.x, free_rect.y + free_rect.h - h),
        (free_rect.x + free_rect.w - w, free_rect.y + free_rect.h - h),
        (free_rect.x + max(0, (free_rect.w - w) // 2), free_rect.y + max(0, (free_rect.h - h) // 2)),
    ]
    seen = set()
    valid: List[Tuple[int, int]] = []
    for x, y in candidates:
        if x < free_rect.x or y < free_rect.y:
            continue
        if x + w > free_rect.x + free_rect.w or y + h > free_rect.y + free_rect.h:
            continue
        if (x, y) in seen:
            continue
        seen.add((x, y))
        valid.append((x, y))
    return valid


def _split_free_rect(free_rect: Rect, placed: Rect) -> List[Rect]:
    pieces: List[Rect] = []

    left_w = placed.x - free_rect.x
    if left_w > 0:
        pieces.append(Rect(free_rect.x, free_rect.y, left_w, free_rect.h))

    right_x = placed.x + placed.w
    right_w = free_rect.x + free_rect.w - right_x
    if right_w > 0:
        pieces.append(Rect(right_x, free_rect.y, right_w, free_rect.h))

    top_h = placed.y - free_rect.y
    if top_h > 0:
        pieces.append(Rect(placed.x, free_rect.y, placed.w, top_h))

    bottom_y = placed.y + placed.h
    bottom_h = free_rect.y + free_rect.h - bottom_y
    if bottom_h > 0:
        pieces.append(Rect(placed.x, bottom_y, placed.w, bottom_h))

    return _prune_free_rects(pieces)


def _area_is_separated(
    area_code: str,
    candidate: Rect,
    layout: Dict[str, Rect],
    must_separate: List[Tuple[str, str]],
) -> bool:
    for a_code, b_code in must_separate:
        if area_code == a_code and b_code in layout and _adjacent(candidate, layout[b_code]):
            return True
        if area_code == b_code and a_code in layout and _adjacent(candidate, layout[a_code]):
            return True
    return False


def _best_greedy_candidate(
    area_code: str,
    required_area: int,
    free_rects: List[Rect],
    layout: Dict[str, Rect],
    facility_width: int,
    facility_height: int,
    must_separate: List[Tuple[str, str]],
) -> Tuple[Rect, Rect] | None:
    dimension_candidates = _dimension_candidates(required_area, facility_width, facility_height)
    dimension_candidates = dimension_candidates[:12]

    for free_rect in free_rects:
        for w, h in dimension_candidates:
            if w > free_rect.w or h > free_rect.h:
                continue
            for x, y in _candidate_positions_in_rect(free_rect, w, h):
                candidate = Rect(x=x, y=y, w=w, h=h)
                if _area_is_separated(area_code, candidate, layout, must_separate):
                    continue
                return candidate, free_rect

    return None


def slp_layout(case: CaseData, score_df) -> LayoutResult:
    start = time.perf_counter()
    facility = case.facility

    area_scores = relation_score(case.areas, score_df)
    ordered = sorted(case.areas, key=lambda a: area_scores[a.code], reverse=True)

    facility_area = facility.width * facility.height
    base_required = [int(math.ceil(a.min_area * (1.0 + case.growth_percent))) for a in ordered]
    sum_base = sum(base_required)
    scaled_required = list(base_required)
    if sum_base > 0 and sum_base < facility_area:
        scale_factor = facility_area / sum_base
        scaled_required = [int(math.ceil(area_required * scale_factor)) for area_required in base_required]

    free_rects: List[Rect] = [Rect(0, 0, facility.width, facility.height)]
    layout: Dict[str, Rect] = {}

    for idx, area in enumerate(ordered):
        required_area = scaled_required[idx]
        best_choice = _best_greedy_candidate(
            area.code,
            required_area,
            free_rects,
            layout,
            facility.width,
            facility.height,
            case.constraints.must_separate,
        )
        if best_choice is None:
            continue

        candidate, used_free_rect = best_choice
        layout[area.code] = candidate
        free_rects.remove(used_free_rect)
        free_rects.extend(_split_free_rect(used_free_rect, candidate))
        free_rects = _prune_free_rects(free_rects)

    runtime_s = time.perf_counter() - start
    violations = _count_hard_violations(layout, case.constraints.must_adjacent, case.constraints.must_separate)
    status = "feasible" if len(layout) == len(ordered) and violations == 0 else "feasible_not_optimal"
    return LayoutResult(layout=layout, runtime_s=runtime_s, status=status, a_hard_violations=violations)
