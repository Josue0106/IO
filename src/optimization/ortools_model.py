from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Set
import math
import time

from ortools.sat.python import cp_model

from core.data_model import Area, CaseData
from core.layout_metrics import Rect


@dataclass(frozen=True)
class OptResult:
    layout: Dict[str, Rect]
    runtime_s: float
    status: str


def _dimension_candidates(min_area: int, max_w: int, max_h: int) -> List[Tuple[int, int]]:
    candidates: List[Tuple[int, int]] = []
    for w in range(1, max_w + 1):
        for h in range(1, max_h + 1):
            if w * h >= min_area:
                candidates.append((w, h))
    candidates.sort(key=lambda wh: (wh[0] * wh[1], abs(wh[0] - wh[1])))
    return candidates[:50]


def solve_layout(case: CaseData, time_limit_s: int = 60, enforce_relations: bool = True) -> OptResult:
    start = time.perf_counter()
    facility = case.facility
    model = cp_model.CpModel()

    x_vars = {}
    y_vars = {}
    w_vars = {}
    h_vars = {}
    x2_center = {}
    y2_center = {}
    x_intervals = {}
    y_intervals = {}

    for area in case.areas:
        required_area = int(math.ceil(area.min_area * (1.0 + case.growth_percent)))
        w = model.NewIntVar(1, facility.width, f"w_{area.code}")
        h = model.NewIntVar(1, facility.height, f"h_{area.code}")
        model.AddAllowedAssignments([w, h], _dimension_candidates(required_area, facility.width, facility.height))

        x = model.NewIntVar(0, facility.width, f"x_{area.code}")
        y = model.NewIntVar(0, facility.height, f"y_{area.code}")
        model.Add(x + w <= facility.width)
        model.Add(y + h <= facility.height)

        x2 = model.NewIntVar(0, 2 * facility.width, f"x2_{area.code}")
        y2 = model.NewIntVar(0, 2 * facility.height, f"y2_{area.code}")
        model.Add(x2 == 2 * x + w)
        model.Add(y2 == 2 * y + h)

        x_end = model.NewIntVar(0, facility.width, f"x_end_{area.code}")
        y_end = model.NewIntVar(0, facility.height, f"y_end_{area.code}")
        model.Add(x_end == x + w)
        model.Add(y_end == y + h)

        x_interval = model.NewIntervalVar(x, w, x_end, f"xint_{area.code}")
        y_interval = model.NewIntervalVar(y, h, y_end, f"yint_{area.code}")

        x_vars[area.code] = x
        y_vars[area.code] = y
        w_vars[area.code] = w
        h_vars[area.code] = h
        x2_center[area.code] = x2
        y2_center[area.code] = y2
        x_intervals[area.code] = x_interval
        y_intervals[area.code] = y_interval

    model.AddNoOverlap2D(list(x_intervals.values()), list(y_intervals.values()))

    terms = []
    for flow in case.flows:
        dx = model.NewIntVar(0, 2 * facility.width, f"dx_{flow.origin}_{flow.dest}")
        dy = model.NewIntVar(0, 2 * facility.height, f"dy_{flow.origin}_{flow.dest}")
        model.AddAbsEquality(dx, x2_center[flow.origin] - x2_center[flow.dest])
        model.AddAbsEquality(dy, y2_center[flow.origin] - y2_center[flow.dest])
        dist = model.NewIntVar(0, 4 * max(facility.width, facility.height), f"dist_{flow.origin}_{flow.dest}")
        model.Add(dist == dx + dy)
        terms.append(dist * flow.value)

    max_dist = 2 * facility.width + 2 * facility.height
    for a_code, b_code in case.constraints.must_adjacent:
        dx = model.NewIntVar(0, 2 * facility.width, f"dx_adj_{a_code}_{b_code}")
        dy = model.NewIntVar(0, 2 * facility.height, f"dy_adj_{a_code}_{b_code}")
        model.AddAbsEquality(dx, x2_center[a_code] - x2_center[b_code])
        model.AddAbsEquality(dy, y2_center[a_code] - y2_center[b_code])
        dist = model.NewIntVar(0, max_dist, f"dist_adj_{a_code}_{b_code}")
        model.Add(dist == dx + dy)
        terms.append(dist * 50)

    for a_code, b_code in case.constraints.must_separate:
        dx = model.NewIntVar(0, 2 * facility.width, f"dx_sep_{a_code}_{b_code}")
        dy = model.NewIntVar(0, 2 * facility.height, f"dy_sep_{a_code}_{b_code}")
        model.AddAbsEquality(dx, x2_center[a_code] - x2_center[b_code])
        model.AddAbsEquality(dy, y2_center[a_code] - y2_center[b_code])
        dist = model.NewIntVar(0, max_dist, f"dist_sep_{a_code}_{b_code}")
        model.Add(dist == dx + dy)
        penalty = model.NewIntVar(0, max_dist, f"pen_sep_{a_code}_{b_code}")
        model.Add(penalty == max_dist - dist)
        terms.append(penalty * 50)

    if enforce_relations:
        _add_relation_constraints(case, model, x_vars, y_vars, w_vars, h_vars)

    model.Minimize(sum(terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s

    status = solver.Solve(model)

    layout = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for area in case.areas:
            layout[area.code] = Rect(
                x=solver.Value(x_vars[area.code]),
                y=solver.Value(y_vars[area.code]),
                w=solver.Value(w_vars[area.code]),
                h=solver.Value(h_vars[area.code]),
            )

    runtime_s = time.perf_counter() - start
    status_name = solver.StatusName(status)
    return OptResult(layout=layout, runtime_s=runtime_s, status=status_name)


def _add_relation_constraints(
    case: CaseData,
    model: cp_model.CpModel,
    x_vars: Dict[str, cp_model.IntVar],
    y_vars: Dict[str, cp_model.IntVar],
    w_vars: Dict[str, cp_model.IntVar],
    h_vars: Dict[str, cp_model.IntVar],
) -> None:
    a_e_pairs: Set[Tuple[str, str]] = set()
    x_pairs: Set[Tuple[str, str]] = set()

    for rel in case.relations:
        if rel.rel in {"A", "E"}:
            a_e_pairs.add(tuple(sorted((rel.a, rel.b))))
        if rel.rel == "X":
            x_pairs.add(tuple(sorted((rel.a, rel.b))))

    for a_code, b_code in sorted(a_e_pairs):
        _add_must_adjacent(model, a_code, b_code, x_vars, y_vars, w_vars, h_vars)

    for a_code, b_code in sorted(x_pairs):
        _add_must_separate(model, a_code, b_code, x_vars, y_vars, w_vars, h_vars)


def _add_must_adjacent(
    model: cp_model.CpModel,
    a_code: str,
    b_code: str,
    x_vars: Dict[str, cp_model.IntVar],
    y_vars: Dict[str, cp_model.IntVar],
    w_vars: Dict[str, cp_model.IntVar],
    h_vars: Dict[str, cp_model.IntVar],
) -> None:
    x_a, y_a, w_a, h_a = x_vars[a_code], y_vars[a_code], w_vars[a_code], h_vars[a_code]
    x_b, y_b, w_b, h_b = x_vars[b_code], y_vars[b_code], w_vars[b_code], h_vars[b_code]

    left = model.NewBoolVar(f"adj_left_{a_code}_{b_code}")
    right = model.NewBoolVar(f"adj_right_{a_code}_{b_code}")
    down = model.NewBoolVar(f"adj_down_{a_code}_{b_code}")
    up = model.NewBoolVar(f"adj_up_{a_code}_{b_code}")

    model.Add(x_a + w_a == x_b).OnlyEnforceIf(left)
    model.Add(y_a + 1 <= y_b + h_b).OnlyEnforceIf(left)
    model.Add(y_b + 1 <= y_a + h_a).OnlyEnforceIf(left)

    model.Add(x_b + w_b == x_a).OnlyEnforceIf(right)
    model.Add(y_a + 1 <= y_b + h_b).OnlyEnforceIf(right)
    model.Add(y_b + 1 <= y_a + h_a).OnlyEnforceIf(right)

    model.Add(y_a + h_a == y_b).OnlyEnforceIf(up)
    model.Add(x_a + 1 <= x_b + w_b).OnlyEnforceIf(up)
    model.Add(x_b + 1 <= x_a + w_a).OnlyEnforceIf(up)

    model.Add(y_b + h_b == y_a).OnlyEnforceIf(down)
    model.Add(x_a + 1 <= x_b + w_b).OnlyEnforceIf(down)
    model.Add(x_b + 1 <= x_a + w_a).OnlyEnforceIf(down)

    model.AddBoolOr([left, right, up, down])


def _add_must_separate(
    model: cp_model.CpModel,
    a_code: str,
    b_code: str,
    x_vars: Dict[str, cp_model.IntVar],
    y_vars: Dict[str, cp_model.IntVar],
    w_vars: Dict[str, cp_model.IntVar],
    h_vars: Dict[str, cp_model.IntVar],
) -> None:
    x_a, y_a, w_a, h_a = x_vars[a_code], y_vars[a_code], w_vars[a_code], h_vars[a_code]
    x_b, y_b, w_b, h_b = x_vars[b_code], y_vars[b_code], w_vars[b_code], h_vars[b_code]

    left_gap = model.NewBoolVar(f"sep_left_{a_code}_{b_code}")
    right_gap = model.NewBoolVar(f"sep_right_{a_code}_{b_code}")
    down_gap = model.NewBoolVar(f"sep_down_{a_code}_{b_code}")
    up_gap = model.NewBoolVar(f"sep_up_{a_code}_{b_code}")

    model.Add(x_a + w_a + 1 <= x_b).OnlyEnforceIf(left_gap)
    model.Add(x_b + w_b + 1 <= x_a).OnlyEnforceIf(right_gap)
    model.Add(y_a + h_a + 1 <= y_b).OnlyEnforceIf(up_gap)
    model.Add(y_b + h_b + 1 <= y_a).OnlyEnforceIf(down_gap)

    model.AddBoolOr([left_gap, right_gap, up_gap, down_gap])
