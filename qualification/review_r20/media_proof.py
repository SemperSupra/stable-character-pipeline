#!/usr/bin/env python3
"""R20 independent original self-authored synthetic two-transport media custody check.

Uses previously captured actual R9 provider artifacts, SHA-bound receipts, and
real bytes. It does not assert an original R009 person, archive or rights PASS.
"""
import argparse,hashlib,json,re,sys
from pathlib import Path
SOURCE="0e07d607b9c0003dbea54e872f82be98bb3fcb84"
CAMERAS=("OriginalFront","OriginalOblique")
SCIENTIFIC=("FAIL_ABSTRACT_LIMBS_ONLY","UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM",
 "HELD_R009_NOT_RUN_NOT_ADMITTED")
class Invalid(ValueError):pass
def need(ok,code):
 if not ok:raise Invalid(code)
def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):
 def unique(pairs):
  out={}
  for k,v in pairs:
   need(k not in out,"RECEIPT_DUPLICATE_FIELD")
   out[k]=v
  return out
 data=path.read_bytes()
 need(len(data)<1048576,"RECEIPT_SIZE_UNBOUNDED")
 return json.loads(data,object_pairs_hook=unique)
def audit(media,evidence):
 records=[]
 for kind in ("cli","http"):
  p=media/("r9-"+kind)/"attempt-0001"/"forward"
  receipt=evidence/("r9-"+kind)/"attempt-0001"/"result.json"
  if not receipt.is_file():
   receipt=evidence/"r9-observed"/(kind+"-result.json")
  need(receipt.is_file() and not receipt.is_symlink(),"ORIGINAL_RECEIPT_MISSING")
  r=load(receipt)
  need(r.get("schema")=="scp.native-job-result.v1" and r.get("revision")==SOURCE,
       "ORIGINAL_SOURCE_REVISION_MISMATCH")
  need((r.get("human_behavior"),r.get("human_anatomy"),r.get("release"))==SCIENTIFIC,
       "ORIGINAL_SCIENTIFIC_RELEASE_HOLD_BYPASS")
  need(r.get("rights")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC","ORIGINAL_SOURCE_RIGHTS_MISMATCH")
  need(r.get("frames")==24 and r.get("fps")==12 and
       r.get("actor_ids")==["CobaltOriginal","MarigoldOriginal"],"SOURCE_CHARACTER_FRAME_MISMATCH")
  video=r.get("video_sha256")
  need(isinstance(video,dict) and set(video)==set(CAMERAS),"TWO_CAMERAS_REQUIRED")
  actual={}
  for name,rel,expected in [
    ("glb",p/"original_synthetic_24frame_skinned.glb",r.get("glb_sha256")),
    ("blend",p/"original_source_grounded_24frame_native.blend",r.get("blend_sha256")),
    *[(cam,p/"rendered"/(cam+".mp4"),video[cam]) for cam in CAMERAS]]:
   need(rel.is_file() and not rel.is_symlink(),"ORIGINAL_MEDIA_MISSING_"+name)
   digest=sha(rel.read_bytes())
   need(type(expected) is str and re.fullmatch("[0-9a-f]{64}",expected) and expected==digest,
        "ORIGINAL_MEDIA_HASH_MISMATCH_"+name)
   actual[name]=digest
  records.append({"kind":kind,"source_sha":r["source_sha256"],"sha":actual})
 need(records[0]["source_sha"]==records[1]["source_sha"],"TWO_TRANSPORT_SOURCE_MISMATCH")
 for name in ("glb",*CAMERAS):
  need(records[0]["sha"][name]==records[1]["sha"][name],"TWO_TRANSPORT_MEDIA_MISMATCH_"+name)
 need(records[0]["sha"]["blend"]!=records[1]["sha"]["blend"],
      "ORIGINAL_BINARY_NONDETERMINISM_OBSERVATION_MISSING")
 return {"schema":"scp.r20.public_synthetic_media_cold_proof.v1",
 "original_source_commit":SOURCE,"source_sha256":records[0]["source_sha"],
 "verified_transport_media_sha":{x:records[0]["sha"][x] for x in ("glb",*CAMERAS)},
 "editable_blend_binary_sha":[r["sha"]["blend"] for r in records],
 "editable_blend_semantics":"REFER_TO_INDEPENDENT_R19_NATIVE_SCENE_WITNESS",
 "original_private_r009":"HELD_NOT_ACCEPTED",
 "artifact_custody":"SOURCE_BYTES_HASH_CHECKED_NOT_SIGNED_RELEASE",
 "decision":"HOLD_RELEASE_AND_CPE_PROMOTION"}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--media",type=Path,required=True)
 p.add_argument("--evidence",type=Path,required=True)
 a=p.parse_args()
 try:out=audit(a.media,a.evidence)
 except (OSError,Invalid,ValueError,TypeError) as e:
  print("R20_FAIL_CLOSED:"+str(e),file=sys.stderr);return 2
 print(json.dumps(out,sort_keys=True,indent=2))
 return 0
if __name__=="__main__":raise SystemExit(main())
