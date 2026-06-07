import time
from core.data_model import load_case
from core.matrices import build_relation_matrix
from slp.heuristic import slp_layout
from optimization.ortools_model import solve_layout
from core.layout_metrics import compute_metrics


def _normalize_layout(layout):
    # layout may be dict[str, Rect]
    return layout


def run_case(path):
    print(f"\n=== Running case: {path} ===")
    case = load_case(path)
    facility_area = case.facility.width * case.facility.height

    _, score_df = build_relation_matrix(case.areas, case.relations, case.relation_weights)

    print("- Running SLP heuristic...")
    slp_res = slp_layout(case, score_df)
    slp_layout_map = _normalize_layout(slp_res.layout)
    print(f"  SLP runtime_s: {slp_res.runtime_s:.4f}")

    print("- Validating SLP geometry within facility...")
    for code, rect in slp_layout_map.items():
        if rect.x < 0 or rect.y < 0 or rect.x + rect.w > case.facility.width or rect.y + rect.h > case.facility.height:
            print(f"  !! SLP rect out of bounds: {code} -> {rect}")

    slp_metrics = compute_metrics(slp_layout_map, case.flows, case.relations, facility_area)
    print("  SLP metrics:")
    for k, v in slp_metrics.items():
        print(f"    {k}: {v}")

    print("- Running OPT (may take up to 60s)...")
    start = time.perf_counter()
    opt_res = solve_layout(case, time_limit_s=60, enforce_relations=True)
    elapsed = time.perf_counter() - start
    print(f"  OPT runtime_s (recorded): {opt_res.runtime_s:.4f}, wall-clock: {elapsed:.4f}, status: {opt_res.status}")

    print("- Validating OPT geometry within facility...")
    for code, rect in opt_res.layout.items():
        if rect.x < 0 or rect.y < 0 or rect.x + rect.w > case.facility.width or rect.y + rect.h > case.facility.height:
            print(f"  !! OPT rect out of bounds: {code} -> {rect}")

    opt_metrics = compute_metrics(opt_res.layout, case.flows, case.relations, facility_area)
    print("  OPT metrics:")
    for k, v in opt_metrics.items():
        print(f"    {k}: {v}")


if __name__ == "__main__":
    examples = [
        "data/example_case_small.json",
        "data/example_case_large.json",
    ]
    for ex in examples:
        run_case(ex)
