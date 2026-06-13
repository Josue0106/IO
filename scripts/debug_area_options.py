import sys
sys.path.insert(0,'src')
from core.data_model import load_case
from core.matrices import build_relation_matrix
from slp.heuristic import _dimension_candidates, _candidate_positions_in_rect

case=load_case('data/example_case_small.json')
_, score_df=build_relation_matrix(case.areas, case.relations, {'A':10,'E':5,'I':-5,'O':0,'U':0,'X':-10})
ordered=case.areas
facility_width=case.facility.width
facility_height=case.facility.height
for idx, area in enumerate(ordered):
    required_area=int((area.min_area*(1.0+case.growth_percent))+0.9999)
    dim_cands=_dimension_candidates(required_area,facility_width,facility_height)
    print(area.code,'required',required_area,'dim_cands',len(dim_cands))
    cnt=0
    for w,h in dim_cands[:200]:
        pos=_candidate_positions_in_rect(type('R',(),{'x':0,'y':0,'w':facility_width,'h':facility_height})(),w,h)
        if pos:
            cnt+=1
    print(' positions for first 200 dims with full free rect:',cnt)
