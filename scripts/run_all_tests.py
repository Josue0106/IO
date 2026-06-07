import os
import io
import matplotlib
matplotlib.use('Agg')

from core.data_model import load_case
from core.matrices import build_relation_matrix
from slp.heuristic import slp_layout
from optimization.ortools_model import solve_layout
from core.layout_metrics import compute_metrics
from core.comparison import build_comparison_df
from visualization.plotting import plot_layout
import pandas as pd

out_dir = 'tests/output'
os.makedirs(out_dir, exist_ok=True)

case = load_case('data/sample_case.json')
rel_df, score_df = build_relation_matrix(case.areas, case.relations, case.relation_weights)

print('Running SLP...')
slp_res = slp_layout(case, score_df)
print(f'SLP runtime: {slp_res.runtime_s:.4f}s, areas: {len(slp_res.layout)}')

print('Running OPT (may take up to 60s)...')
opt_res = solve_layout(case, time_limit_s=60, enforce_relations=True)
print(f'OPT runtime: {opt_res.runtime_s:.4f}s, status: {opt_res.status}, areas: {len(opt_res.layout)}')

# Save layouts CSV
slp_rows = [{'code':k,'x':r.x,'y':r.y,'w':r.w,'h':r.h} for k,r in slp_res.layout.items()]
opt_rows = [{'code':k,'x':r.x,'y':r.y,'w':r.w,'h':r.h} for k,r in opt_res.layout.items()]
slp_df = pd.DataFrame(slp_rows)
opt_df = pd.DataFrame(opt_rows)
slp_df.to_csv(os.path.join(out_dir,'layout_slp.csv'), index=False)
opt_df.to_csv(os.path.join(out_dir,'layout_opt.csv'), index=False)

# Save PNGs
fig_slp = plot_layout(slp_res.layout, case.facility.width, case.facility.height, 'SLP')
fig_slp.savefig(os.path.join(out_dir,'layout_slp.png'), bbox_inches='tight')
fig_opt = plot_layout(opt_res.layout, case.facility.width, case.facility.height, 'OPT')
fig_opt.savefig(os.path.join(out_dir,'layout_opt.png'), bbox_inches='tight')

# Metrics and comparison
slp_metrics = compute_metrics(slp_res.layout, case.flows, case.relations, case.facility.width*case.facility.height)
slp_metrics['runtime_s'] = slp_res.runtime_s
opt_metrics = compute_metrics(opt_res.layout, case.flows, case.relations, case.facility.width*case.facility.height)
opt_metrics['runtime_s'] = opt_res.runtime_s
opt_metrics['solver_status'] = opt_res.status

metrics_data = [('SLP', slp_metrics), ('OPT', opt_metrics)]
comparison_df = build_comparison_df(metrics_data)
comparison_df.to_csv(os.path.join(out_dir,'comparison_detailed.csv'), index=False)

# Summary
print('Saved:')
print(' -', os.path.join(out_dir,'layout_slp.csv'))
print(' -', os.path.join(out_dir,'layout_slp.png'))
print(' -', os.path.join(out_dir,'layout_opt.csv'))
print(' -', os.path.join(out_dir,'layout_opt.png'))
print(' -', os.path.join(out_dir,'comparison_detailed.csv'))
