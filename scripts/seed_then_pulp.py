import sys
import math

sys.path.insert(0, 'src')

from core.data_model import load_case
from core.matrices import build_relation_matrix
from slp.heuristic import slp_layout
from optimization.pulp_model import solve_layout as pulp_solve


def seed_from_slp(case):
    _, score_df = build_relation_matrix(case.areas, case.relations, {'A': 10, 'E': 5, 'I': -5, 'O': 0, 'U': 0, 'X': -10})
    res = slp_layout(case, score_df)
    seed = {}
    for code, rect in res.layout.items():
        seed[code] = (rect.w, rect.h)
    print('SLP placed', len(seed), 'areas, status=', res.status)
    return seed, res


def run(path):
    case = load_case(path)
    seed, slp_res = seed_from_slp(case)
    # if SLP produced a full tiling (no free space), fix sizes in PuLP for faster, robust optimization
    if slp_res.status == 'feasible':
        print('SLP returned full tiling — fixing sizes in PuLP')
        res = pulp_solve(case, time_limit_s=180, seed_sizes=seed, seed_fix=True)
    else:
        # otherwise allow PuLP to adjust sizes (relaxed coverage handled in model)
        res = pulp_solve(case, time_limit_s=180, seed_sizes=seed, seed_fix=False)
    print('\nPULP on', path)
    print(' pulp status=', res.status, 'layout_size=', len(res.layout), 'obj=', res.objective_value, 'runtime=', res.runtime_s)


def main():
    for p in ['data/example_case_small.json', 'data/example_case_large.json']:
        run(p)


if __name__ == '__main__':
    main()
