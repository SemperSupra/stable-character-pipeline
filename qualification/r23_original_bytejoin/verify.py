#!/usr/bin/env python3
"""Exact original public synthetic source/camera bytes; NOT real human gait or issuer signature."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"review_r21"))
from pixel_approach import source_bound_approach, MotionError
SHA={"source":"c1ebf84b60bacaf4d1132f88dcfd588c9b94fa1790a3e48f163dfd195e22b449",
"front":"edcb3fb1ebec9ff9d381681559e8398baf438ca19214110e2ad47a8284d97aeb",
"oblique":"68a8d1147bc98f38d883f201fcfc7a0bc2e6afe2550c1744a9edffed43034672"}
def assess(source,front,oblique):
 paths={"source":Path(source),"front":Path(front),"oblique":Path(oblique)}
 actual={}
 for name,path in paths.items():
  if not path.is_file() or path.stat().st_size>2000000:raise MotionError("R23_FILE_MISSING_OR_UNBOUNDED")
  actual[name]=hashlib.sha256(path.read_bytes()).hexdigest()
  if actual[name]!=SHA[name]:raise MotionError("R23_SOURCE_CAMERA_ROLE_SHA_MISMATCH:"+name)
 s=json.loads(paths["source"].read_bytes())
 if s.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":raise MotionError("R23_RIGHTS_NOT_PINNED")
 geometry=source_bound_approach(s,{"OriginalFront":paths["front"],"OriginalOblique":paths["oblique"]})
 if geometry["human_behavior"]!="FAIL_ABSTRACT_LIMBS_ONLY" or geometry["biological_jcs_rom"]!="UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM" or geometry["r009_private"]!="HELD_R009_NOT_RUN_NOT_ADMITTED":raise MotionError("R23_SCIENCE_ESCALATED")
 return {"schema":"scp.r23.public_original_pinned_byte_roles.v1","qualification":"PASS_ORIGINAL_PUBLIC_SYNTHETIC_SOURCE_CAMERA_BYTES_ONLY",
 "sha256":actual,"original_run":41225967024,"issuer":"UNKNOWN_NOT_AUTHENTICATED",
 "visual":geometry,"anatomy":"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM",
 "human_motion":"FAIL_ABSTRACT_LIMBS_ONLY","R009":"HELD_R009_NOT_RUN_NOT_ADMITTED"}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source");p.add_argument("--front");p.add_argument("--oblique")
 p.add_argument("--capabilities",action="store_true")
 a=p.parse_args()
 if a.capabilities:
  print(json.dumps({"schema":"scp.r23.public_original_pinned_byte_roles.v1","actions":["capabilities","inspect_read_only"],"writer_actions":[],"release":"HELD"}));return 0
 if not all((a.source,a.front,a.oblique)):p.error("required source, front, oblique")
 try:print(json.dumps(assess(a.source,a.front,a.oblique),sort_keys=True));return 0
 except (OSError,ValueError,KeyError,TypeError) as e:print("R23_FAIL_CLOSED:"+str(e),file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
