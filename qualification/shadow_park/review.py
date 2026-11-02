#!/usr/bin/env python3
"""Independent adversarial oracle for original synthetic two-person park motion.
No imported source bytes or identity/protected-data claims, and no acceptance
by simply trusting the producer receipt. All frames, both actors, both feet.
"""
import argparse,copy,hashlib,json,math,pathlib,sys

ACTORS=("CobaltOriginal","MarigoldOriginal")
SIDES=("left","right")
EXPECTED_CAMERAS={
 "front":{"position":[0.,-7.2,3.4],"target":[0.,0.,1.2]},
 "oblique":{"position":[5.,-6.,3.7],"target":[0.,0.,1.2]},
}
def dist(a,b):
 return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def check(scene):
 violations=[]
 def require(ok,reason):
  if not ok and reason not in violations:violations.append(reason)
 require(scene.get("schema")=="scp.shadow.original-two-actor.v1","WRONG_TRACE_SCHEMA")
 require(scene.get("source_class")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC","NONORIGINAL_SOURCE")
 require(scene.get("private_r009")=="HELD_NOT_ACCEPTED","UNAUTHORIZED_PRIVATE_PRODUCT_PROMOTION")
 require(scene.get("measured_human")=="NOT_ADMITTED","FALSE_REAL_HUMAN_ADMISSION")
 require(scene.get("authentic_identity")=="NOT_VERIFIED","FALSE_CHARACTER_IDENTITY")
 require(scene.get("fps")==12 and scene.get("frame_count")==72,"WRONG_FRAME_CLOCK")
 require(scene.get("actor_ids")==list(ACTORS),"WRONG_ACTOR_SET")
 require(scene.get("cameras")==EXPECTED_CAMERAS,"CAMERA_ROLE_OR_EXTRINSIC_FORGERY")
 frames=scene.get("frames",[])
 if len(frames)!=72:return ["INVALID_FRAME_COUNT"]+violations
 feet_held={k:{s:0 for s in SIDES} for k in ACTORS}
 foot_swing={k:{s:False for s in SIDES} for k in ACTORS}
 move={k:[] for k in ACTORS}
 offset_angles={k:{s:[] for s in SIDES} for k in ACTORS}
 last_feet={}
 for idx,frame in enumerate(frames):
  require(frame.get("frame")==idx and abs(frame.get("time_seconds",-999)-idx/12)<2e-9,"FRAME_TIME_OR_ORDER_MISMATCH")
  actors=frame.get("actors",{})
  if set(actors)!=set(ACTORS):
   require(False,"WRONG_PER_FRAME_ACTOR_SET")
   continue
  for actor in ACTORS:
   state=actors[actor]
   root=state.get("root_x_m")
   if not isinstance(root,(int,float)) or not math.isfinite(root):
    require(False,"INVALID_ROOT")
    continue
   move[actor].append(root)
   bones=state.get("bones",{})
   require(len(bones)==13,"MISSING_ARTICULATED_BONE")
   for name,link in bones.items():
    for term in ("head","tail"):
     p=link.get(term,[])
     require(len(p)==3 and all(isinstance(x,(float,int)) and math.isfinite(x) for x in p),"NONFINITE_OR_MISSING_BONE_POSITION")
   for side in SIDES:
    thigh=bones.get(side+"_thigh",{})
    shin=bones.get(side+"_shin",{})
    foot=bones.get(side+"_foot",{})
    if not all(x.get("head") and x.get("tail") for x in (thigh,shin,foot)):
     require(False,"MISSING_LEG_KINEMATIC_CHAIN")
     continue
    hip,knee,ankle=thigh["head"],thigh["tail"],shin["tail"]
    require(dist(knee,shin["head"])<2e-6,"KNEE_JOINT_DISCONNECTED")
    require(dist(ankle,foot["head"])<2e-6,"ANKLE_JOINT_DISCONNECTED")
    require(abs(dist(hip,knee)-.49)<2e-5,"THIGH_LENGTH_OR_HYPEREXTENSION")
    require(abs(dist(knee,ankle)-.48)<2e-5,"SHIN_LENGTH_OR_HYPEREXTENSION")
    u=[hip[i]-knee[i] for i in range(3)]
    v=[ankle[i]-knee[i] for i in range(3)]
    nu,nv=dist(u,[0,0,0]),dist(v,[0,0,0])
    if nu>0 and nv>0:
     angle=math.degrees(math.acos(max(-1.,min(1.,sum(a*b for a,b in zip(u,v))/(nu*nv)))))
     # This is only a conservative synthetic joint guard; NOT clinical ROM.
     require(95.<=angle<=178.,"SYNTHETIC_KNEE_ROM_ENVELOPE")
    f=state.get("feet",{}).get(side,{})
    require(len(f.get("ankle",[]))==3 and dist(f["ankle"],ankle)<2e-6,"UNBOUND_FOOT_CONTACT_RECEIPT")
    lift=f.get("lift_m")
    require(type(lift) in (int,float) and 0.<=lift<=.1001,"INVALID_SWING_CLEARANCE")
    require(ankle[2]>=.0999,"BELOW_GROUND_ANKLE")
    foot_swing[actor][side]|=lift>.055
    if f.get("contact") is True:
     require(lift<=1e-5,"FALSE_CONTACT_WHILE_SWINGING")
     prev=last_feet.get((actor,side))
     if prev and prev[0]:
      slip=math.hypot(prev[1][0]-ankle[0],prev[1][1]-ankle[1])
      require(slip<.008,"FOOT_CONTACT_SLIDING")
      feet_held[actor][side]+=1
    last_feet[(actor,side)]=(f.get("contact") is True,ankle)
    offset_angles[actor][side].append((knee[0]-hip[0],knee[1]-hip[1]))
  if len(actors)==2:
   delta=actors[ACTORS[1]]["root_x_m"]-actors[ACTORS[0]]["root_x_m"]
   require(delta>1.9,"TWO_ACTOR_COLLISION_OR_ROLE_ALIAS")
 for actor in ACTORS:
  roots=move[actor]
  if len(roots)!=72:continue
  approach=1 if actor==ACTORS[0] else -1
  require(all(approach*(b-a)>=-1e-8 for a,b in zip(roots,roots[1:])),"ROOT_RETROGRADE")
  require(approach*(roots[-1]-roots[0])>2.,"NO_TWO_ACTOR_APPROACH")
  require(max(abs(x-y) for x,y in zip(roots[60:],roots[61:]))<1e-8,"FAIL_TO_STOP")
  for side in SIDES:
   require(feet_held[actor][side]>=12,"INSUFFICIENT_PLANTED_FOOT_EVIDENCE")
   require(foot_swing[actor][side],"NO_FOOT_LIFT_IN_SWING")
   arr=offset_angles[actor][side]
   if len(arr)==72:
    require(math.dist(arr[0],arr[12])>.025,"ROOT_ONLY_FROZEN_GAIT")
 return violations

def mutate(scene,scenario):
 if scenario=="baseline":return
 if scenario=="sliding":
  f=scene["frames"][3]["actors"][ACTORS[0]]
  f["feet"]["left"]["ankle"][0]+=.14
 elif scenario=="hyperextension":
  f=scene["frames"][12]["actors"][ACTORS[0]]
  f["bones"]["left_thigh"]["tail"][2]+=.25
  f["bones"]["left_shin"]["head"][2]+=.25
 elif scenario=="root_only":
  for actor in ACTORS:
   pose=scene["frames"][0]["actors"][actor]
   target=scene["frames"][12]["actors"][actor]
   dx=target["root_x_m"]-pose["root_x_m"]
   for name,link in target["bones"].items():
    for key in ("head","tail"):
     link[key]=[p+dx if i==0 else p for i,p in enumerate(pose["bones"][name][key])]
 elif scenario=="swapped_cameras":
  scene["cameras"]["oblique"]=copy.deepcopy(scene["cameras"]["front"])
 elif scenario=="claimed_human":
  scene["private_r009"]="ACCEPTED"
  scene["measured_human"]="ADMITTED"
 elif scenario=="aliased_actor":
  for f in scene["frames"]:
   f["actors"][ACTORS[1]]=copy.deepcopy(f["actors"][ACTORS[0]])
 elif scenario=="wrong_clock":
  scene["frames"][17]["time_seconds"]+=.08
 else:raise ValueError("UNKNOWN_FAULT_SCENARIO")

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--input",required=True)
 parser.add_argument("--fault",default="baseline",choices=["baseline","sliding","hyperextension","root_only","swapped_cameras","claimed_human","aliased_actor","wrong_clock"])
 parser.add_argument("--out",required=True)
 args=parser.parse_args()
 source=pathlib.Path(args.input).read_bytes()
 scene=json.loads(source)
 mutate(scene,args.fault)
 problems=check(scene)
 expect=(args.fault!="baseline")
 if expect:
  passed=bool(problems)
  label="PASS_EXPECTED_SYNTHETIC_RED_REJECTED" if passed else "FAIL_MUTANT_FALSE_ACCEPTED"
 else:
  passed=not problems
  label="PASS_SYNTHETIC_GROUNDTRUTH_ENGINEERING_ONLY" if passed else "FAIL_SYNTHETIC_BASELINE"
 result={"schema":"scp.shadow.adversarial-review.v1","status":label,
   "scenario":args.fault,"source_sha256":hashlib.sha256(source).hexdigest(),
   "violations":problems,"expected_rejection":expect,"review_passed":passed,
   "tested_actor_count":2,"tested_frame_count":72,
   "original_human_asset":"NOT_ADMITTED",
   "physical_biomechanics":"UNKNOWN_NOT_INDEPENDENTLY_MEASURED",
   "private_r009":"HELD_NOT_ACCEPTED"}
 with pathlib.Path(args.out).open("x",encoding="utf-8") as f:
  json.dump(result,f,sort_keys=True,indent=2);f.write("\n")
 print(json.dumps(result,sort_keys=True))
 if not passed:sys.exit(2)
if __name__=="__main__":main()
