import os
import time

from core.data_model import load_case
from core.matrices import build_relation_matrix
from slp.heuristic import slp_layout
from optimization.ortools_model import solve_layout


def test_slp_runs_and_returns_layout():
    case = load_case("data/sample_case.json")
    _, score_df = build_relation_matrix(case.areas, case.relations, case.relation_weights)
    res = slp_layout(case, score_df)
    assert res.layout, "SLP returned empty layout"
    assert res.runtime_s > 0


def test_opt_runs_and_returns_layout_within_limit():
    case = load_case("data/sample_case.json")
    # run with the same limit as the UI to ensure no regressions
    start = time.perf_counter()
    res = solve_layout(case, time_limit_s=60, enforce_relations=True)
    elapsed = time.perf_counter() - start
    # solver should produce a layout (may be feasible) and respect the time limit
    assert res.layout, "OPT returned empty layout"
    assert isinstance(res.runtime_s, float)
    assert elapsed <= 70, f"Solver exceeded wall-clock threshold: {elapsed}s"
