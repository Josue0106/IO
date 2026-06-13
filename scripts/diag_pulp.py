import sys
import math

sys.path.insert(0, 'src')

from core.data_model import load_case
from optimization.pulp_model import solve_layout as pulp_solve


def run(path):
    case = load_case(path)
    print('\nCase:', path)
    print(' Facility area:', case.facility.width * case.facility.height)
    res = pulp_solve(case, time_limit_s=30)
    print(' status=', res.status, 'layout_size=', len(res.layout), 'obj=', res.objective_value, 'runtime=', res.runtime_s)


def main():
    for p in ['data/example_case_small.json', 'data/example_case_large.json']:
        run(p)


if __name__ == '__main__':
    main()
