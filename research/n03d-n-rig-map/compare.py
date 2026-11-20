"""Independent comparison of real R090+N03D-M observed foot/shoe velocities.
Uses actual source-derived metrics and checks provenance, never promotes a gait.
"""
import json,sys,math,hashlib
from pathlib import Path
def compare(report,scenario):
 if scenario not in ("baseline","symmetric"):raise ValueError("UNKNOWN_SCENARIO")
 if report.get("schema")!="scp.n03d-m.source60hz-fk-vs-retarget-foot24hz.v1":raise ValueError("NOT_SOURCE_REAL_NATIVE")
 if report.get("foot_contact_accepted") is not False or report.get("mvp_accepted") is not False:raise ValueError("FALSE_NATIVE_ACCEPTANCE")
 actors=report.get("actors")
 if not isinstance(actors,list) or sorted(x["actor"] for x in actors)!=["AsterOriginal","JuniperOriginal"]:raise ValueError("WRONG_NATIVE_ACTOR_SET")
 out=[]
 for actor in actors:
  sides=actor.get("source_vs_native")
  if not isinstance(sides,list) or sorted(s["rig_side"] for s in sides)!=["L","R"]:raise ValueError("BAD_FOOT_SIDE_WITNESS")
  for side in sides:
   for k in ("native_foot_head_near_p50_mps","source_ankle_near_p50_mps","direct_label_speed_ratio"):
    if type(side.get(k)) not in (float,int) or not math.isfinite(side[k]) or side[k]<0:raise ValueError("NONFINITE_VELOCITY")
   out.append({"actor":actor["actor"],"side":side["rig_side"],
     "source_ankle_p50_mps":side["source_ankle_near_p50_mps"],
     "native_foot_p50_mps":side["native_foot_head_near_p50_mps"],
     "source_ratio":side["direct_label_speed_ratio"],
     "gait_accepted":False})
 return {"schema":"scp.n03d-n.real-source-map-comparison.v1","scenario":scenario,
  "source_scene_sha256":report["source_scene_sha256"],
  "target_observed":out,
  "technical_retarged":True,"causal_mapping_improvement_established":False,
  "joint_rom_qualified":False,"physical_shoe_contact_accepted":False,"mvp_accepted":False,
  "release_authorized":False}
if __name__=="__main__":
 try:
  if len(sys.argv)!=4:raise ValueError("USAGE")
  p=Path(sys.argv[1]);r=json.loads(p.read_text())
  outcome=compare(r,sys.argv[2]);outcome["source_receipt_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest()
  Path(sys.argv[3]).write_text(json.dumps(outcome,indent=2,sort_keys=True,allow_nan=False)+"\n")
  print("N03D_N_REAL_MAP_BAKEOFF",json.dumps({"scenario":outcome["scenario"],"actors":outcome["target_observed"],"contact_accepted":False},sort_keys=True),flush=True)
 except (ValueError,TypeError,KeyError,OSError) as e:
  print("N03D_N_SOURCE_MAP_RED",repr(e),file=sys.stderr);sys.exit(12)
