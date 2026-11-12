"""Fail-closed measured world-scale contract, independently computed."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--native',required=True,type=Path)
p.add_argument('--glb',required=True,type=Path)
p.add_argument('--receipt',required=True,type=Path)
a=p.parse_args()
n=json.loads(a.native.read_text());g=json.loads(a.glb.read_text())
nn=float(n['extent_world'][2]);gg=float(g['extent_world'][2])
ratio=gg/nn if nn>1e-12 else None
errors=[]
if not (1.3<=nn<=2.2): errors.append('native_height_outside_human_meter_envelope')
if not (1.3<=gg<=2.2): errors.append('glb_height_outside_human_meter_envelope')
if ratio is None or not 0.98<=ratio<=1.02: errors.append('relative_scale_mismatch_gt_2_percent')
r={'status':'PASS_SCALE_ONLY' if not errors else 'FAIL_SCALE_QUALIFICATION',
   'native_height_world':nn,'glb_height_world':gg,'height_ratio':ratio,
   'errors':errors,'units_assumption':'Blender world coordinates mapped to meters',
   'limits':['Neutral pose only','Not pose-corrective/rig/animation parity','Not physiological stature fit']}
a.receipt.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
print('R014_MHR_SCALE_GATE',json.dumps(r,sort_keys=True))
raise SystemExit(bool(errors))
