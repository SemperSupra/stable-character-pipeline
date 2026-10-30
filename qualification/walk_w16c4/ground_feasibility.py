"""W16-C4 synthetic grounded sole/heel/toe feasibility source and gate.

C3 rest hip is z=1.4, two 0.6 links cannot reach a ground ankle z=0
even at zero horizontal separation; changing only foot-pose labels is invalid.
This source defines NEW explicit abstract hip z=1.08 feasibility candidate.
Not integrated into C3 Blender native rig or realistic anatomical walking.
"""
import argparse,hashlib,json,math
from pathlib import Path
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
FRAMES=tuple(range(24))
FPS=12
THIGH=SHIN=.60
HIP_Z=1.08
SOLE_HALF=.12
SKATE_TOL=.001
GROUND_TOL=.0001
def sub(a,b):return tuple(a[k]-b[k] for k in range(3))
def add(a,b):return tuple(a[k]+b[k] for k in range(3))
def scale(a,v):return tuple(x*v for x in a)
def dot(a,b):return sum(a[k]*b[k] for k in range(3))
def length(a):return math.sqrt(dot(a,a))
def solve(hip,ankle,pole):
 ray=sub(ankle,hip);dist=length(ray)
 if not(0.001<dist<THIGH+SHIN-1e-6):raise ValueError("C4_UNREACHABLE_GROUNDED_TARGET")
 direction=scale(ray,1/dist)
 p=sub(pole,hip)
 perp=sub(p,scale(direction,dot(p,direction)))
 if length(perp)<1e-8:raise ValueError("C4_POLE_DEGENERATE")
 side=scale(perp,1/length(perp))
 along=(THIGH*THIGH-SHIN*SHIN+dist*dist)/(2*dist)
 height=math.sqrt(THIGH*THIGH-along*along)
 knee=add(hip,add(scale(direction,along),scale(side,height)))
 if abs(length(sub(knee,hip))-THIGH)>1e-8 or abs(length(sub(ankle,knee))-SHIN)>1e-8:
  raise ValueError("C4_IK_SEGMENT")
 return knee
def original(profile):
 if profile not in ("forward","outward"):raise ValueError("C4_PROFILE")
 direction=1 if profile=="forward" else -1
 actors=[]
 for name,x in (("CobaltOriginal",-1.65),("MarigoldOriginal",1.65)):
  frames=[]
  for i in FRAMES:
   root_y=direction*.16*i/23
   legs=[]
   for label,sign,offset in (("Left",-1,0),("Right",1,6)):
    phase=(i+offset)%12
    stance=phase<6
    # Canonical anchor ties all stance frames to one physical ground point.
    cycle_start=i-phase
    anchor_y=direction*.16*cycle_start/23
    next_anchor=direction*.16*(cycle_start+12)/23
    if stance:
     ay=anchor_y;z=0.
    else:
     u=(phase-6+1)/6
     ay=anchor_y+(next_anchor-anchor_y)*u
     z=.045*math.sin(math.pi*u)+.025
    hip=(x+sign*.22,root_y,HIP_Z)
    ankle=(hip[0],ay,z)
    pole=(hip[0]+sign*.25,hip[1]+direction*.36,hip[2]-.4)
    knee=solve(hip,ankle,pole)
    heel=(ankle[0],ankle[1]-direction*SOLE_HALF,ankle[2])
    toe=(ankle[0],ankle[1]+direction*SOLE_HALF,ankle[2])
    legs.append({"id":label,"state":"stance" if stance else "swing",
     "anchor":None if not stance else (hip[0],anchor_y,0.),
     "hip":hip,"knee":knee,"ankle":ankle,"heel":heel,"toe":toe,
     "pole":pole,"source_rights":RIGHTS})
   frames.append({"index":i,"time_num":i,"time_den":12,"legs":legs,
    "root_y":root_y})
  actors.append({"id":name,"frames":frames})
 return {"schema":"scp.walk_c4_original_ground_feasibility.v1","rights":RIGHTS,
  "profile":profile,"fps_num":FPS,"fps_den":1,
  "source_motion":"NEW_ORIGINAL_PROCEDURAL_NOT_C3_SOURCE_OR_NATIVE",
  "rest_hip_height":HIP_Z,"bone_lengths":[THIGH,SHIN],
  "source_basis":"BLENDER_WORLD_Z_UP","actors":actors}
def verify(p):
 if p.get("schema")!="scp.walk_c4_original_ground_feasibility.v1" or p.get("rights")!=RIGHTS:
  raise ValueError("C4_RIGHTS_OR_SCHEMA")
 if p.get("rest_hip_height")!=HIP_Z or p.get("bone_lengths")!=[THIGH,SHIN] or p.get("fps_num")!=12 or p.get("fps_den")!=1:
  raise ValueError("C4_REST_OR_CLOCK")
 if len(p.get("actors",[]))!=2:raise ValueError("C4_TWO_ACTORS")
 min_clear=math.inf;max_stance_drift=0.;stance_count=0;swing_count=0
 for a in p["actors"]:
  if len(a["frames"])!=24:raise ValueError("C4_FRAME_COUNT")
  previous={};prior_any={};max_frame_step=0.
  for i,f in enumerate(a["frames"]):
   if (f["index"],f["time_num"],f["time_den"])!=(i,i,12):raise ValueError("C4_CLOCK")
   if len(f["legs"])!=2:raise ValueError("C4_LEG_COUNT")
   for li,leg in enumerate(f["legs"]):
    if leg["id"]!=("Left","Right")[li] or leg["source_rights"]!=RIGHTS:
     raise ValueError("C4_LEG_RIGHTS")
    for key in ("hip","knee","ankle","heel","toe"):
     v=leg[key]
     if len(v)!=3 or any(not math.isfinite(x) for x in v):raise ValueError("C4_NONFINITE")
    if abs(length(sub(leg["hip"],leg["knee"]))-THIGH)>1e-8 or abs(length(sub(leg["ankle"],leg["knee"]))-SHIN)>1e-8:
     raise ValueError("C4_BONE_FK")
    if leg["id"] in prior_any:
     step=length(sub(leg["ankle"],prior_any[leg["id"]]))
     max_frame_step=max(max_frame_step,step)
     if step>.045:raise ValueError("C4_ABRUPT_FOOT_JUMP")
    prior_any[leg["id"]]=leg["ankle"]
    min_clear=min(min_clear,leg["heel"][2],leg["toe"][2])
    if min(leg["heel"][2],leg["toe"][2]) < -GROUND_TOL:raise ValueError("C4_GROUND_PENETRATION")
    if leg["state"]=="stance":
     stance_count+=1
     if leg["anchor"] is None or abs(leg["heel"][2])>GROUND_TOL or abs(leg["toe"][2])>GROUND_TOL:
      raise ValueError("C4_FALSE_STANCE")
     if length(sub(leg["ankle"],leg["anchor"]))>SKATE_TOL:raise ValueError("C4_STANCE_ANCHOR")
     if leg["id"] in previous:
      drift=length(sub(leg["ankle"],previous[leg["id"]]))
      max_stance_drift=max(max_stance_drift,drift)
      if drift>SKATE_TOL:raise ValueError("C4_PLANTED_SLIP")
     previous[leg["id"]]=leg["ankle"]
    elif leg["state"]=="swing":
     swing_count+=1
     if leg["anchor"] is not None or min(leg["heel"][2],leg["toe"][2])<.02:
      raise ValueError("C4_SWING_CLEARANCE")
     previous.pop(leg["id"],None)
    else:raise ValueError("C4_CONTACT_STATE")
 if stance_count!=48 or swing_count!=48:raise ValueError("C4_STANCE_SWING_COUNT")
 return {"schema":"scp.walk_c4_feasibility_receipt.v1",
  "status":"PASS_ABSTRACT_GROUNDED_KINEMATIC_CANDIDATE_ONLY",
  "actors":2,"source_frames":24,"legs":4,"stance_samples":stance_count,
  "swing_samples":swing_count,"min_sole_z":min_clear,
  "max_source_stance_drift":max_stance_drift,
  "max_frame_ankle_step":max_frame_step,
  "current_C3_native_hip_height":1.4,"current_C3_native_max_leg_reach":1.2,
  "current_C3_can_reach_ground_with_this_rest":False,
  "native_skinning":"NOT_BUILT_NOT_ADMITTED",
  "visual_full_body":"RED_UNQUALIFIED_ABSTRACT_PROTOTYPE",
  "foot_anatomy":"PROCEDURAL_MARKERS_NOT_HUMAN_SOURCE"}
def main():
 p=argparse.ArgumentParser();p.add_argument("--profile",choices=("forward","outward"),required=True)
 p.add_argument("--out",required=True);a=p.parse_args()
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 source=original(a.profile);r=verify(source)
 raw=json.dumps(source,sort_keys=True,indent=2)+"\n"
 (out/"source.json").write_text(raw)
 r["source_sha256"]=hashlib.sha256(raw.encode()).hexdigest()
 (out/"receipt.json").write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print("W16C4_GROUND_REACH_FEASIBILITY_PASS",a.profile,r["max_source_stance_drift"])
if __name__=="__main__":main()
