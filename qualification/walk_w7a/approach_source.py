"""W7A ORIGINAL abstract two-actor world-X approach, with genuine fixed world stance.

A new source scenario, NOT a retroactive C4 motion/biological gait correction.
Conservative synthetic geometry. Body deformation, true anatomy and human gait
remain independently unqualified.
"""
import argparse,copy,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"walk_w16c4"))
import ground_feasibility as c4
RIGHTS=c4.RIGHTS
SCHEMA="scp.walk_w7a_original_approach.v1"
MAX_X_TRAVEL=.40
def generate(profile):
 p=copy.deepcopy(c4.original(profile))
 direction=1 if profile=="forward" else -1
 p["schema"]=SCHEMA
 p["scenario"]="ORIGINAL_2ACTOR_WORLD_X_APPROACH_NOT_HUMAN_GAIT"
 p["root_x_travel_per_actor"]=MAX_X_TRAVEL
 p["knee_pole_basis"]="ARTIFICIAL_SAGITTAL_FORWARD_Y_NO_ANATOMICAL_JCS"
 for ai,actor in enumerate(p["actors"]):
  x0=(-1.65,1.65)[ai]
  towards=1 if ai==0 else -1
  for f in actor["frames"]:
   i=f["index"]
   new_x=x0+towards*MAX_X_TRAVEL*i/23
   f["root_x"]=new_x
   for li,leg in enumerate(f["legs"]):
    sign=(-1,1)[li]
    phase=(i+(0,6)[li])%12
    cycle_start=i-phase
    last=x0+towards*MAX_X_TRAVEL*cycle_start/23+sign*.22
    future=x0+towards*MAX_X_TRAVEL*(cycle_start+12)/23+sign*.22
    if leg["state"]=="stance":
     axle_x=last
     leg["anchor"]=(last,leg["anchor"][1],0.)
    else:
     u=(phase-6+1)/6
     axle_x=last+(future-last)*u
    hip=(new_x+sign*.22,leg["hip"][1],c4.HIP_Z)
    ankle=(axle_x,leg["ankle"][1],leg["ankle"][2])
    pole=(hip[0],hip[1]+direction*.42,hip[2]-.40)
    knee=c4.solve(hip,ankle,pole)
    leg["hip"]=hip;leg["ankle"]=ankle;leg["knee"]=knee;leg["pole"]=pole
    leg["heel"]=(axle_x,leg["heel"][1],leg["heel"][2])
    leg["toe"]=(axle_x,leg["toe"][1],leg["toe"][2])
 return p

def verify(p):
 if p.get("schema")!=SCHEMA or p.get("rights")!=RIGHTS or p.get("scenario")!="ORIGINAL_2ACTOR_WORLD_X_APPROACH_NOT_HUMAN_GAIT" or p.get("root_x_travel_per_actor")!=MAX_X_TRAVEL:
  raise ValueError("W7_SOURCE_RIGHTS_SCENARIO")
 if p.get("knee_pole_basis")!="ARTIFICIAL_SAGITTAL_FORWARD_Y_NO_ANATOMICAL_JCS":
  raise ValueError("W7_UNTRUSTED_KNEE_POLE")
 mechanical=copy.deepcopy(p)
 mechanical["schema"]="scp.walk_c4_original_ground_feasibility.v1"
 original=c4.verify(mechanical)
 if original["max_frame_ankle_step"]>.045 or original["max_source_stance_drift"]>c4.SKATE_TOL:
  raise ValueError("W7_FOOT_JUMP_OR_PLANTED_SKATE")
 samples=[]
 for ai,actor in enumerate(p["actors"]):
  x0=(-1.65,1.65)[ai]
  sign=1 if ai==0 else -1
  seen=[]
  for i,f in enumerate(actor["frames"]):
   expected_x=x0+sign*MAX_X_TRAVEL*i/23
   if not math.isclose(f.get("root_x",math.nan),expected_x,rel_tol=0,abs_tol=1e-10):
    raise ValueError("W7_ROOT_NOT_SOURCE_TRAJECTORY")
   for li,leg in enumerate(f["legs"]):
    if abs(leg["hip"][0]-(expected_x+(-1,1)[li]*.22))>1e-9:
     raise ValueError("W7_HIP_ROOT_BIND")
    if abs(leg["pole"][0]-leg["hip"][0])>1e-9:
     raise ValueError("W7_UNAUTHORIZED_LATERAL_POLE")
    lateral=abs(leg["knee"][0]-leg["hip"][0])
    if lateral>.145:
     raise ValueError("W7_EXCESS_LATERAL_KNEE_DEVIATION")
    seen.append(lateral)
  samples.append(max(seen))
 root_distances=[p["actors"][1]["frames"][i]["root_x"]-p["actors"][0]["frames"][i]["root_x"] for i in range(24)]
 if abs(root_distances[0]-3.3)>1e-10 or abs(root_distances[-1]-2.5)>1e-10:
  raise ValueError("W7_ACTOR_APPROACH_NOT_MEASURED")
 if any(root_distances[i+1]>=root_distances[i] for i in range(23)):
  raise ValueError("W7_NOT_STRICT_APPROACH")
 return {"schema":"scp.walk_w7a_original_approach_source_receipt.v1",
  "status":"PASS_ORIGINAL_SOURCE_X_APPROACH_PLANTED_CONTACT_ONLY",
  "rights":RIGHTS,"profile":p["profile"],"fps":12,"source_frames":24,
  "root_separation_start":root_distances[0],"root_separation_end":root_distances[-1],
  "source_hip_height":c4.HIP_Z,"source_links":[c4.THIGH,c4.SHIN],
  "max_lateral_knee_deviation":max(samples),
  "max_source_planted_heel_slip":original["max_source_stance_drift"],
  "max_source_ankle_frame_step":original["max_frame_ankle_step"],
  "source_contact_scope":"WORLD_FIXED_STANCE_ONLY_NO_FORCE_OR_FRICTION",
  "human_joint_rom":"UNKNOWN_NO_VERIFIED_JCS_OR_NORMATIVE_ANGLE",
  "complete_approach":"PARTIAL_APPROACH_NO_MEETING_NOT_R009"}
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--profile",choices=("forward","outward"),required=True)
 a.add_argument("--out",required=True)
 opts=a.parse_args()
 out=Path(opts.out);out.mkdir(parents=True,exist_ok=True)
 s=generate(opts.profile);r=verify(s)
 raw=json.dumps(s,indent=2,sort_keys=True)+"\n"
 (out/"source.json").write_text(raw)
 r["source_sha256"]=hashlib.sha256(raw.encode()).hexdigest()
 (out/"receipt.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 print("W7_SOURCE_APPROACH_PLANTED_PASS",opts.profile, r["root_separation_start"],r["root_separation_end"],r["max_source_ankle_frame_step"])
if __name__=="__main__":main()
