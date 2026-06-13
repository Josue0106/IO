from __future__ import annotations

from typing import Dict, List, Tuple
import math
import time

import pulp

from core.data_model import CaseData
from core.layout_metrics import Rect, compute_metrics
from optimization.ortools_model import OptResult


def _dimension_candidates(min_area: int, max_w: int, max_h: int) -> List[Tuple[int, int]]:
    candidates: List[Tuple[int, int]] = []
    for w in range(1, max_w + 1):
        for h in range(1, max_h + 1):
            if w * h >= min_area:
                candidates.append((w, h))
    candidates.sort(key=lambda wh: (wh[0] * wh[1], abs(wh[0] - wh[1])))
    return candidates


def _build_area_choice_terms(
    case: CaseData,
    facility_w: int,
    facility_h: int,
        prob: pulp.LpProblem,
    seed_sizes: dict | None = None,
    seed_fix: bool = False,
) -> tuple[dict, dict, dict, dict, list[str]]:
    w_exprs = {}
    h_exprs = {}
    area_exprs = {}
    required_area_by_code = {}
    codes = []

    MAX_CANDIDATES = 80
    for area in case.areas:
        required_area = int(math.ceil(area.min_area * (1.0 + case.growth_percent)))
        required_area_by_code[area.code] = required_area
        codes.append(area.code)

        candidates = _dimension_candidates(required_area, facility_w, facility_h)
        if not candidates:
            s = int(math.ceil(math.sqrt(required_area)))
            candidates = [(s, s)]

        candidates.sort(key=lambda wh, required_area=required_area: abs(wh[0] * wh[1] - required_area))
        candidates = candidates[:MAX_CANDIDATES]

        if seed_fix and seed_sizes and area.code in seed_sizes:
            sw, sh = seed_sizes[area.code]
            candidates = [(sw, sh)]

        choice_vars = [pulp.LpVariable(f"choice_{area.code}_{idx}", cat='Binary') for idx in range(len(candidates))]
        prob.addConstraint(pulp.lpSum(choice_vars) == 1)
        w_exprs[area.code] = pulp.lpSum(choice_vars[idx] * candidates[idx][0] for idx in range(len(candidates)))
        h_exprs[area.code] = pulp.lpSum(choice_vars[idx] * candidates[idx][1] for idx in range(len(candidates)))
        area_exprs[area.code] = pulp.lpSum(choice_vars[idx] * (candidates[idx][0] * candidates[idx][1]) for idx in range(len(candidates)))

    return w_exprs, h_exprs, area_exprs, required_area_by_code, codes


def _add_non_overlap_constraints(
    prob: pulp.LpProblem,
    codes: list[str],
    xc,
    yc,
    w_exprs,
    h_exprs,
    facility_w: int,
    facility_h: int,
):
    b = {}
    pair_codes = [(codes[i], codes[j]) for i in range(len(codes)) for j in range(i + 1, len(codes))]
    for i, j in pair_codes:
        b[(i, j, 'L')] = pulp.LpVariable(f"b_{i}_{j}_L", cat='Binary')
        b[(i, j, 'R')] = pulp.LpVariable(f"b_{i}_{j}_R", cat='Binary')
        b[(i, j, 'A')] = pulp.LpVariable(f"b_{i}_{j}_A", cat='Binary')
        b[(i, j, 'B')] = pulp.LpVariable(f"b_{i}_{j}_B", cat='Binary')

    M = facility_w + facility_h
    half_w = {c: w_exprs[c] / 2.0 for c in codes}
    half_h = {c: h_exprs[c] / 2.0 for c in codes}

    for i, j in pair_codes:
            prob.addConstraint(xc[i] - xc[j] + half_w[i] + half_w[j] <= M * (1 - b[(i, j, 'L')]))
            prob.addConstraint(xc[j] - xc[i] + half_w[i] + half_w[j] <= M * (1 - b[(i, j, 'R')]))
            prob.addConstraint(yc[i] - yc[j] + half_h[i] + half_h[j] <= M * (1 - b[(i, j, 'A')]))
            prob.addConstraint(yc[j] - yc[i] + half_h[i] + half_h[j] <= M * (1 - b[(i, j, 'B')]))
            prob.addConstraint(b[(i, j, 'L')] + b[(i, j, 'R')] + b[(i, j, 'A')] + b[(i, j, 'B')] >= 1)


def _build_objective_terms(case: CaseData, model: pulp.LpProblem, xc, yc):
    delta_x = {}
    delta_y = {}
    for i in [a.code for a in case.areas]:
        for j in [a.code for a in case.areas]:
            if i >= j:
                continue
            delta_x[(i, j)] = pulp.LpVariable(f"dx_{i}_{j}", lowBound=0, cat='Continuous')
            delta_y[(i, j)] = pulp.LpVariable(f"dy_{i}_{j}", lowBound=0, cat='Continuous')
            model.addConstraint(delta_x[(i, j)] >= xc[i] - xc[j])
            model.addConstraint(delta_x[(i, j)] >= xc[j] - xc[i])
            model.addConstraint(delta_y[(i, j)] >= yc[i] - yc[j])
            model.addConstraint(delta_y[(i, j)] >= yc[j] - yc[i])

    objective_terms = []
    for flow in case.flows:
        key = tuple(sorted((flow.origin, flow.dest)))
        dx = delta_x.get(key)
        dy = delta_y.get(key)
        if dx is not None and dy is not None and flow.value > 0:
            objective_terms.append(flow.value * dx)
            objective_terms.append(flow.value * dy)

    return objective_terms


def solve_layout(case: CaseData, time_limit_s: int = 120, seed_sizes: dict | None = None, seed_fix: bool = False) -> OptResult:
    start = time.perf_counter()
    facility_w = case.facility.width
    facility_h = case.facility.height
    facility_area = facility_w * facility_h

    areas = case.areas
    codes = [a.code for a in areas]

    prob = pulp.LpProblem("layout_pulp", pulp.LpMinimize)

    xc = {c: pulp.LpVariable(f"xc_{c}", lowBound=0, upBound=facility_w, cat='Continuous') for c in codes}
    yc = {c: pulp.LpVariable(f"yc_{c}", lowBound=0, upBound=facility_h, cat='Continuous') for c in codes}

    w_exprs, h_exprs, area_exprs, _, codes = _build_area_choice_terms(
        case,
        facility_w,
        facility_h,
        prob,
        seed_sizes=seed_sizes,
        seed_fix=seed_fix,
    )

    half_w = {c: w_exprs[c] / 2.0 for c in codes}
    half_h = {c: h_exprs[c] / 2.0 for c in codes}

    for c in codes:
            prob.addConstraint(xc[c] - half_w[c] >= 0)
            prob.addConstraint(xc[c] + half_w[c] <= facility_w)
            prob.addConstraint(yc[c] - half_h[c] >= 0)
            prob.addConstraint(yc[c] + half_h[c] <= facility_h)

    _add_non_overlap_constraints(prob, codes, xc, yc, w_exprs, h_exprs, facility_w, facility_h)

    # allow unused area but penalize it in the objective so optimizer prefers full coverage
    unused_area = pulp.LpVariable("unused_area", lowBound=0, upBound=facility_area, cat='Continuous')
    prob.addConstraint(pulp.lpSum(area_exprs.values()) + unused_area == facility_area)

    objective_terms = _build_objective_terms(case, prob, xc, yc)
    flow_sum = sum((f.value for f in case.flows)) if case.flows else 1.0
    penalty_per_unit = max(1.0, flow_sum) * max(facility_w, facility_h)

    prob += pulp.lpSum(objective_terms) + penalty_per_unit * unused_area

    solver = pulp.PULP_CBC_CMD(timeLimit=time_limit_s, msg=False)
    prob.solve(solver)

    status_name = pulp.LpStatus.get(prob.status, "Unknown")

    layout = {}
    if prob.status not in (-1, -2, -3):
        for c in codes:
            xcent = pulp.value(xc[c])
            ycent = pulp.value(yc[c])
            w_val = pulp.value(w_exprs[c])
            h_val = pulp.value(h_exprs[c])
            if xcent is None or ycent is None or w_val is None or h_val is None:
                layout = {}
                break
            x = max(0, xcent - w_val / 2.0)
            y = max(0, ycent - h_val / 2.0)
            layout[c] = Rect(x=int(round(x)), y=int(round(y)), w=int(round(w_val)), h=int(round(h_val)))

    runtime_s = time.perf_counter() - start
    objective_value = float(pulp.value(prob.objective)) if pulp.value(prob.objective) is not None else float("nan")
    if layout:
        metrics = compute_metrics(layout, case.flows, case.relations, facility_area)
        if math.isnan(objective_value):
            objective_value = float(metrics["flow_distance"])
    return OptResult(layout=layout, runtime_s=runtime_s, status=status_name, objective_value=objective_value)
