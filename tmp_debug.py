from core.data_model import load_case
from core.matrices import build_relation_matrix, relation_score
from slp.heuristic import _choose_dimensions
import math

c=load_case('data/sample_case.json')
rel,score=build_relation_matrix(c.areas,c.relations,c.relation_weights)
scores=relation_score(c.areas, score)
ordered=sorted(c.areas, key=lambda a: scores[a.code], reverse=True)
print('order',[a.code for a in ordered])
base_required=[int(math.ceil(a.min_area*(1.0+c.growth_percent))) for a in ordered]
print('base_required',base_required,'sum',sum(base_required))
fa=c.facility.width*c.facility.height
scale=1.0
scaled=base_required
if sum(base_required)>0 and sum(base_required)<fa:
    scale=fa/sum(base_required)
    scaled=[int(math.ceil(b*scale)) for b in base_required]
    excess=sum(scaled)-fa
    print('scale',scale,'scaled',scaled,'excess',excess)
    idxs=list(range(len(scaled)))
    while excess>0:
        reducible=[(i, scaled[i]-base_required[i]) for i in idxs if scaled[i]-base_required[i]>0]
        if not reducible:
            break
        reducible.sort(key=lambda x:x[1],reverse=True)
        i=reducible[0][0]
        scaled[i]-=1
        excess-=1
print('final scaled',scaled,'sum',sum(scaled))
for req,a in zip(scaled,ordered):
    try:
        w,h=_choose_dimensions(req,c.facility.width,c.facility.height)
    except Exception as e:
        print('choose failed for',a.code,req,e)
        w,h=None,None
    print(a.code,req,'->',w,h)
