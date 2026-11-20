"""N03D-P GPL Diffeomorphic known-rig target map structural coverage evidence.
No source code rewrite in author repo, no unjustified fix or natural gait acceptance.
"""
import argparse,json,hashlib
from pathlib import Path
EXPECTED=("upperleg01","upperleg02","lowerleg01","lowerleg02","foot")
def summarize(data):
 if not isinstance(data,dict) or data.get("name")!="MakeHuman":raise ValueError("NOT_EXACT_PUBLISHED_MAKEHUMAN_MAP")
 bones=data.get("bones")
 if not isinstance(bones,dict):raise ValueError("NOT_A_BONE_DICT")
 for k,v in bones.items():
  if not isinstance(k,str) or not isinstance(v,str) or not k or not v:raise ValueError("EMPTY_MAP_KEY")
 coverage={}
 for side in ("L","R"):
  names=[x+"."+side for x in EXPECTED]
  mapped={x:bones.get(x) for x in names}
  canonical=list(x for x in mapped.values() if x is not None)
  if len(canonical)!=len(set(canonical)):raise ValueError("DUPLICATE_CANONICAL_LEG_BONE")
  coverage[side]={"known_five_link_chain":names,"mapped":mapped,
   "missing_native_chain_nodes":[x for x in names if x not in bones],
   "mapped_native_chain_nodes":len(names)-sum(x not in bones for x in names),
   "canonical_thigh_twist_in_use":bones.get("upperleg02."+side)=="thigh_twist."+side,
   "canonical_shin_in_use":bones.get("lowerleg01."+side)=="shin."+side,
   "physical_heel_toe_calibrated":False}
 asymmetric=[name for name in EXPECTED if (name+".L" in bones)!=(name+".R" in bones)]
 return {"schema":"scp.n03d-p.upstream-makehuman-map-structural-audit.v1",
  "publisher":"Diffeomorphic GPL-2.0-or-later tool mapping",
  "covered_native_leg_structure":coverage,
  "asymmetric_leg_mapping_stems":asymmetric,
  "missing_distal_shin_both_sides":all("lowerleg02."+s not in bones for s in ("L","R")),
  "fully_source_163_bone_rig_mapped":False,
  "source_ankle_stationarity_accepted":False,"physical_gait_accepted":False,
  "mvp_accepted":False,"release_authorized":False}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 a=p.parse_args()
 obj=json.loads(Path(a.source).read_text())
 report=summarize(obj)
 report["source_sha256"]=hashlib.sha256(Path(a.source).read_bytes()).hexdigest()
 report["source_git_blob_sha1"]="65a49435cc726f2089373caa34373909ff0f2a8e"
 Path(a.out).write_text(json.dumps(report,sort_keys=True,indent=2)+chr(10))
 print("N03D_P_PINNED_MAKEHUMAN_MAP_COVERAGE",json.dumps(report,sort_keys=True),flush=True)
if __name__=="__main__":main()
