"""Source verified in-run GPL known_rigs MakeHuman JSON variant, never a production patch."""
import argparse,hashlib,json
from pathlib import Path
SOURCE_BLOB="65a49435cc726f2089373caa34373909ff0f2a8e"
VARIANTS=("symmetric_twist","distal_shin","distal_thigh_shin")
def git_blob(data):
 return hashlib.sha1(("blob "+str(len(data))+"\0").encode()+data).hexdigest()
def apply(data,variant):
 if variant not in VARIANTS:raise ValueError("UNKNOWN_MAPPING_VARIANT")
 if data.get("name")!="MakeHuman" or not isinstance(data.get("bones"),dict):raise ValueError("NOT_UPSTREAM_MAKEHUMAN")
 out=json.loads(json.dumps(data))
 bones=out["bones"]
 if bones.get("upperleg01.L")!="thigh.L" or bones.get("lowerleg01.R")!="shin.R" or bones.get("upperleg02.L")!="thigh_twist.L":raise ValueError("UPSTREAM_CHAIN_CHANGED")
 if variant=="symmetric_twist":
  if "upperleg02.R" in bones:raise ValueError("PUBLISHED_ASYMMETRY_ALREADY_FIXED")
  bones["upperleg02.R"]="thigh_twist.R"
 elif variant=="distal_shin":
  for side in ("L","R"):
   del bones["lowerleg01."+side]
   bones["lowerleg02."+side]="shin."+side
 elif variant=="distal_thigh_shin":
  for side in ("L","R"):
   del bones["upperleg01."+side]
   if "upperleg02."+side in bones:del bones["upperleg02."+side]
   bones["upperleg02."+side]="thigh."+side
   del bones["lowerleg01."+side]
   bones["lowerleg02."+side]="shin."+side
 canonical=out["bones"]
 for side in ("L","R"):
  for tag in ("thigh."+side,"shin."+side,"foot."+side):
   if sum(v==tag for v in canonical.values())!=1:raise ValueError("DUPLICATE_OR_MISSING_CANONICAL_LEG")
 return out
def main():
 p=argparse.ArgumentParser()
 for n in ("source","out","receipt","variant"):p.add_argument("--"+n,required=True)
 a=p.parse_args()
 raw=Path(a.source).read_bytes()
 if git_blob(raw)!=SOURCE_BLOB:raise ValueError("UPSTREAM_GPL_MAP_BLOB_NOT_PINNED")
 after=apply(json.loads(raw),a.variant)
 cooked=(json.dumps(after,indent=2,sort_keys=True)+"\n").encode()
 if cooked==raw:raise ValueError("VARIANT_NOT_CHANGED")
 Path(a.out).write_bytes(cooked)
 doc={"schema":"scp.n03d-q.ephemeral-upstream-target-map-variant.v1",
 "variant":a.variant,"upstream_git_blob_sha1":SOURCE_BLOB,
 "published_upstream_vendor":"Diffeomorphic/retarget_bvh@a4f2a394901d043457a9426f0d9e2ade9cda702c",
 "modified_known_map_sha256":hashlib.sha256(cooked).hexdigest(),
 "modified_map_git_blob_sha1":git_blob(cooked),
 "vendor_GPL_tool_change_ephemeral_only":True,"published_map_replaced_in_author_repo":False,
 "anatomical_rig_accepted":False,"natural_gait_accepted":False,"mvp_accepted":False}
 Path(a.receipt).write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n")
 print("N03D_Q_EXACT_PUBLISHER_MAP_OVERLAY",json.dumps(doc,sort_keys=True),flush=True)
if __name__=="__main__":main()
