from core.data_model import load_case
from core.matrices import build_relation_matrix, relation_score
from slp.heuristic import _choose_dimensions, _adjacent_candidates, _fits, _seed_positions
from core.layout_metrics import Rect
import math

c=load_case('data/sample_case.json')
rel,score=build_relation_matrix(c.areas,c.relations,c.relation_weights)
scores=relation_score(c.areas, score)
ordered=sorted(c.areas, key=lambda a: scores[a.code], reverse=True)
base_required=[int(math.ceil(a.min_area*(1.0+c.growth_percent))) for a in ordered]
fa=c.facility.width*c.facility.height
scale=1.0
scaled=base_required
if sum(base_required)>0 and sum(base_required)<fa:
    scale=fa/sum(base_required)
    scaled=[int(math.ceil(b*scale)) for b in base_required]
    excess=sum(scaled)-fa
    idxs=list(range(len(scaled)))
    while excess>0:
        reducible=[(i, scaled[i]-base_required[i]) for i in idxs if scaled[i]-base_required[i]>0]
        if not reducible:
            break
        reducible.sort(key=lambda x:x[1],reverse=True)
        i=reducible[0][0]
        scaled[i]-=1
        excess-=1

print('ordered', [a.code for a in ordered])
print('scaled', scaled, 'sum', sum(scaled))

layout={}
for idx, area in enumerate(ordered):
    req=scaled[idx]
    w,h=_choose_dimensions(req, c.facility.width, c.facility.height)
    print('placing',area.code,'req',req,'dim',w,h)
    if idx==0:
        seed_opts=_seed_positions(c.facility.width,c.facility.height,w,h)
        print('seed',seed_opts[0])
        x,y=seed_opts[0]
        layout[area.code]=Rect(x=x,y=y,w=w,h=h)
        continue
    candidate_points=_adjacent_candidates(layout,w,h,c.facility.width,c.facility.height)
    if not candidate_points:
        candidate_points=[(x,y) for x in range(0,c.facility.width-w+1) for y in range(0,c.facility.height-h+1)]
    placed=False
    for x,y in candidate_points:
        if not _fits(layout,x,y,w,h):
            continue
        layout[area.code]=Rect(x=x,y=y,w=w,h=h)
        placed=True
        break
    print('placed?',placed)

print('final layout len', len(layout))
for k,v in layout.items():
    print(k, v)
print('area sum', sum(r.w*r.h for r in layout.values()))
