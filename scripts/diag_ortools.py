import sys
import math

sys.path.insert(0, 'src')

from core.data_model import load_case
from optimization.ortools_model import solve_layout as opt_solve


def main():
    path = 'data/example_case_large.json'
    case = load_case(path)
    print('Facility:', case.facility.width, case.facility.height, 'area=', case.facility.width * case.facility.height)
    print('Areas:', [a.code for a in case.areas])
    print('Relations:', [(r.a, r.b, r.rel) for r in case.relations])

    print('\nRun OR-Tools with enforce_relations=True (60s)')
    res = opt_solve(case, time_limit_s=60, enforce_relations=True)
    print(' status=', res.status, 'layout_size=', len(res.layout), 'obj=', res.objective_value)

    print('\nRun OR-Tools with enforce_relations=False (60s)')
    res2 = opt_solve(case, time_limit_s=60, enforce_relations=False)
    print(' status=', res2.status, 'layout_size=', len(res2.layout), 'obj=', res2.objective_value)


if __name__ == '__main__':
    main()
