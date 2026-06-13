import sys
import math

sys.path.insert(0, 'src')

from core.data_model import load_case
from optimization.pulp_model import _dimension_candidates

MAX_CANDIDATES = 20
MAX_ASPECT_RATIO = 4.0


def list_for(path):
    case = load_case(path)
    print('\nCase:', path)
    for a in case.areas:
        required_area = int(math.ceil(a.min_area * (1.0 + case.growth_percent)))
        all_cands = _dimension_candidates(required_area, case.facility.width, case.facility.height)
        filtered = [wh for wh in all_cands if (1.0 / MAX_ASPECT_RATIO) <= (wh[0] / wh[1]) <= MAX_ASPECT_RATIO]
        if not filtered:
            s = int(math.ceil(math.sqrt(required_area)))
            filtered = [(s, s)]
        print(' Area', a.code, 'required', required_area, 'all:', len(all_cands), 'filtered:', len(filtered), 'sample:', filtered[:6])


def main():
    for p in ['data/example_case_small.json', 'data/example_case_large.json']:
        list_for(p)


if __name__ == '__main__':
    main()
