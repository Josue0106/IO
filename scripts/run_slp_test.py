from core.data_model import load_case
from core.matrices import build_relation_matrix
from slp.heuristic import slp_layout

case = load_case("data/sample_case.json")
rel_df, score_df = build_relation_matrix(case.areas, case.relations, case.relation_weights)
res = slp_layout(case, score_df)
print(f"runtime_s={res.runtime_s:.4f}")
print(f"n_areas={len(res.layout)}")
for k, r in res.layout.items():
    print(k, r)
