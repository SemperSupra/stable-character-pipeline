import json,hashlib,sys,math
from pathlib import Path
from config import variant_settings
def transform(r,v):
 settings=variant_settings(v)
 if r.get('schema')!='scp.n03d-m.source60hz-fk-vs-retarget-foot24hz.v1' or r.get('source_class')!='ORIGINAL_FICTIONAL_MPFBCORE_CC0':raise ValueError('SOURCE_SCHEMA')
 if r.get('foot_contact_accepted') is not False or r.get('mvp_accepted') is not False:raise ValueError('FALSE_ACCEPTANCE')
 actors=r.get('actors')
 if not isinstance(actors,list) or sorted(a.get('actor') for a in actors)!=['AsterOriginal','JuniperOriginal']:raise ValueError('ACTOR_SET')
 rows=[]
 for actor in actors:
  feet=actor.get('source_vs_native')
  if not isinstance(feet,list) or sorted(f.get('rig_side') for f in feet)!=['L','R']:raise ValueError('RIG_SIDE_MISSING')
  for foot in feet:
   for field in ('source_ankle_near_p50_mps','native_foot_head_near_p50_mps'):
    x=foot.get(field)
    if type(x) not in (float,int) or not math.isfinite(x) or x<0:raise ValueError('INVALID_SPEED')
   rows.append({'actor':actor['actor'],'side':foot['rig_side'],'source_mps':foot['source_ankle_near_p50_mps'],'target_mps':foot['native_foot_head_near_p50_mps']})
 return {'schema':'scp.n03d-o.native-factorial.v1','variant':v,'settings':settings,'source_scene_sha256':r['source_scene_sha256'],'foot_speed':rows,'sole_contact_accepted':False,'mvp_accepted':False,'release_authorized':False}
if __name__=='__main__':
 try:
  if len(sys.argv)!=4:raise ValueError('USAGE')
  p=Path(sys.argv[1]);r=transform(json.loads(p.read_text()),sys.argv[2]);r['source_json_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
  Path(sys.argv[3]).write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n')
  print('N03D_O_ACTUAL_FACTORIAL',json.dumps(r,sort_keys=True,allow_nan=False),flush=True)
 except (ValueError,KeyError,TypeError,OSError) as e:
  print('N03D_O_RED',repr(e),file=sys.stderr);sys.exit(12)
