from core.data_model import load_case
from optimization.pulp_model import solve_layout

if __name__ == '__main__':
    case = load_case('data/sample_full_tiling.json')
    res = solve_layout(case, time_limit_s=30)
    print('status=', res.status, 'layout_size=', len(res.layout), 'obj=', res.objective_value, 'time=', res.runtime_s)
    for k,v in res.layout.items():
        print(k, v)
