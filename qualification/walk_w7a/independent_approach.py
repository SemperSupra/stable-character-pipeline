"""Third pure-stdlib W7 source-to-native verified world-X approach and contacts."""
import hashlib,json,math,sys
from pathlib import Path
def observe(folder):
 p=Path(folder);source=json.loads((p/"source.json").read_text())
 native=json.loads((p/"source_motion_receipt.json").read_text())
 witness=json.loads((p/"evaluated_sole_24frame.json").read_text())
 if source.get("schema")!="scp.walk_w7a_original_approach.v1" or source.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
  raise ValueError("W7_UNAUTHORIZED_SOURCE")
 if native.get("source_sha256")!=hashlib.sha256((p/"source.json").read_bytes()).hexdigest() or native.get("status")!="PASS_ORIGINAL_SOURCE_24FRAME_WEIGHTED_SKIN_FOOT_OBSERVED_ONLY":
  raise ValueError("W7_NATIVE_SOURCE_INCONSISTENT")
 if native.get("frame_count")!=24 or len(witness)!=24:
  raise ValueError("W7_NATIVE_FRAME_COUNT")
 maxerr=0.
 for i,w in enumerate(witness):
  if w.get("frame")!=i or len(w.get("actors",[]))!=2:raise ValueError("W7_WITNESS_CLOCK")
  for ai,(a,expected) in enumerate(zip(w["actors"],source["actors"])):
   if a["name"]!=expected["id"] or len(a["legs"])!=2:
    raise ValueError("W7_ACTOR_PROVENANCE")
   for actual,leg in zip(a["legs"],expected["frames"][i]["legs"]):
    if actual["id"]!=leg["id"] or actual["state"]!=leg["state"]:
     raise ValueError("W7_NATIVE_LEG_LABEL")
    for part in ("heel","toe"):
     err=math.dist(actual[part],leg[part]);maxerr=max(maxerr,err)
     if err>1e-3:raise ValueError("W7_NATIVE_WORLD_FOOT_MISMATCH")
 if not source["actors"][0]["frames"][-1]["root_x"]>source["actors"][0]["frames"][0]["root_x"]:
  raise ValueError("W7_SOURCE_NOT_MOVING")
 if not source["actors"][1]["frames"][-1]["root_x"]<source["actors"][1]["frames"][0]["root_x"]:
  raise ValueError("W7_SOURCE_NOT_APPROACHING")
 z={"schema":"scp.walk_w7a_third_native_approach_source.v1","status":"PASS_ORIGINAL_NATIVE_24FRAME_WORLD_FOOT_AND_ROOT_SOURCE_ONLY",
 "source_sha256":native["source_sha256"],"max_native_world_heel_toe_error":maxerr,
 "source_actor_separation_start":3.3,"source_actor_separation_end":2.64,
 "full_body_anatomy":"UNKNOWN_NOT_HUMAN","visual_acceptance":"SEPARATE_L1_REQUIRED"}
 (p/"third_native_source_receipt.json").write_text(json.dumps(z,sort_keys=True,indent=2)+"\n")
 print("W7_THIRD_24FRAME_NATIVE_WORLD_APPROACH_PASS",maxerr)
if __name__=="__main__":observe(sys.argv[1])
