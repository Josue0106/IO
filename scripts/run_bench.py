import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import List

import pandas as pd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))

from core.data_model import load_case
from core.layout_metrics import compute_metrics
from core.matrices import build_relation_matrix
from optimization.ortools_model import solve_layout
from slp.heuristic import slp_layout


def parse_float_list(values: List[str]) -> List[float]:
    return [float(v.strip()) for v in values if v.strip()]


def run_case(case, enforce_relations: bool, time_limit_s: int):
    rel_df, score_df = build_relation_matrix(case.areas, case.relations, case.relation_weights)

    slp_result = slp_layout(case, score_df)
    slp_metrics = compute_metrics(
        slp_result.layout,
        case.flows,
        case.relations,
        case.facility.width * case.facility.height,
    )
    slp_metrics["runtime_s"] = slp_result.runtime_s
    slp_metrics["status"] = "OK"

    opt_result = solve_layout(case, time_limit_s=time_limit_s, enforce_relations=enforce_relations)
    opt_metrics = {"status": opt_result.status, "runtime_s": opt_result.runtime_s}
    if opt_result.layout:
        opt_metrics.update(
            compute_metrics(
                opt_result.layout,
                case.flows,
                case.relations,
                case.facility.width * case.facility.height,
            )
        )

    return slp_metrics, opt_metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch runs for SLP vs Opt")
    parser.add_argument("--input", nargs="+", default=["data/sample_case.json"], help="JSON case files")
    parser.add_argument("--growth", nargs="*", default=["0.0", "0.1", "0.2"], help="Growth percents")
    parser.add_argument("--enforce", choices=["true", "false", "both"], default="both")
    parser.add_argument("--time-limit", type=int, default=10)
    parser.add_argument("--out", default="data/bench_results.csv")
    args = parser.parse_args()

    growth_values = parse_float_list(args.growth)
    enforce_flags = [True, False] if args.enforce == "both" else [args.enforce == "true"]

    rows = []
    for input_path in args.input:
        case = load_case(input_path)
        case_name = Path(input_path).stem
        for growth in growth_values:
            case_variant = replace(case, growth_percent=growth)
            for enforce in enforce_flags:
                slp_metrics, opt_metrics = run_case(case_variant, enforce, args.time_limit)

                rows.append(
                    {
                        "case": case_name,
                        "growth_percent": growth,
                        "enforce_relations": enforce,
                        "method": "SLP",
                        **slp_metrics,
                    }
                )
                rows.append(
                    {
                        "case": case_name,
                        "growth_percent": growth,
                        "enforce_relations": enforce,
                        "method": "OPT",
                        **opt_metrics,
                    }
                )

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    print(f"Wrote {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
