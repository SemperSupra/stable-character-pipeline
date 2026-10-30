"""Independent pure stdlib binary GLB topology and source receipt witness."""
import hashlib,json,struct,sys
from pathlib import Path
def verify(folder):
 p=Path(folder);r=json.loads((p/"native_firstframe_receipt.json").read_text())
 s=json.loads((p/"source.json").read_text())
 if r["source_rights"]!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or s["rights"]!=r["source_rights"]:
  raise ValueError("C5A_SOURCE_RIGHTS")
 if r["scope"]!="ONE_FRAME_NO_24_FRAME_SKIN_COVERAGE_NO_FULL_BODY_NO_L1_IMAGE_ACCEPTANCE":
  raise ValueError("C5A_OVERCLAIMED_ACCEPTANCE")
 if len(r["actors"])!=2 or any(a["bones"]!=6 or a["vertices"]!=48 for a in r["actors"]):
  raise ValueError("C5A_NATIVE_TOPOLOGY")
 for a,sactor in zip(r["actors"],s["actors"]):
  if a["actor"]!=sactor["id"]:raise ValueError("C5A_ACTOR_ORIGIN")
  for leg,source in zip(a["legs"],sactor["frames"][0]["legs"]):
   if leg["leg"]!=source["id"] or leg["state"]!=source["state"]:
    raise ValueError("C5A_CONTACT_SOURCE_MATCH")
   for label in ("heel","toe"):
    if max(abs(x-y) for x,y in zip(leg["observed"][label],source[label]))>1e-3:
     raise ValueError("C5A_NATIVE_SOLE_POSITION")
   if source["state"]=="stance" and abs(leg["native_swept_sole_min_height"])>1e-3:
    raise ValueError("C5A_FALSE_PLANTED")
   if source["state"]=="swing" and leg["native_swept_sole_min_height"]<.02:
    raise ValueError("C5A_FALSE_SWING")
 raw=(p/"source.json").read_bytes()
 if hashlib.sha256(raw).hexdigest()!=r["source_sha256"]:
  raise ValueError("C5A_SOURCE_HASH")
 glb=(p/"source_first_frame_six_bone_foot.glb").read_bytes()
 if hashlib.sha256(glb).hexdigest()!=r["native_glb_sha256"]:
  raise ValueError("C5A_GLB_SHA")
 if len(glb)<100 or glb[:4]!=b"glTF":raise ValueError("C5A_GLB_HEADER")
 magic,version,total=struct.unpack_from("<III",glb)
 if version!=2 or total!=len(glb):raise ValueError("C5A_GLB_LENGTH")
 jlen,jtype=struct.unpack_from("<II",glb,12)
 if jtype!=0x4e4f534a:raise ValueError("C5A_GLB_JSON")
 gltf=json.loads(glb[20:20+jlen].decode())
 if len(gltf.get("skins",[]))!=2 or len(gltf.get("meshes",[]))<2:
  raise ValueError("C5A_TWO_NATIVE_SKINNED_ACTORS")
 joint_counts=[len(x["joints"]) for x in gltf["skins"]]
 if any(v<6 for v in joint_counts):raise ValueError("C5A_SIX_DEFORM_BONES")
 return {"schema":"scp.walk_c5a_independent_binary_glb_receipt.v1",
  "status":"PASS_ORIGINAL_GLB_TOPOLOGY_AND_SOURCE_HEEL_TOE_FIRSTFRAME",
  "source_sha256":r["source_sha256"],"glb_sha256":r["native_glb_sha256"],
  "profile":r["profile"],"joint_counts":joint_counts,
  "native_source_error":r["max_native_joint_landmark_error"],
  "scope":"SINGLE_FIRSTFRAME_NO_GLTF_SKIN_ANIMATION_GEOMETRY_COVERAGE_NO_FULL_BODY"}
if __name__=="__main__":
 a=Path(sys.argv[1]);z=verify(a)
 (a/"third_binary_receipt.json").write_text(json.dumps(z,indent=2,sort_keys=True)+"\n")
 print("W16C5A_THIRD_BINARY_GLB_AND_CONTACT_SOURCE_PASS",z["profile"],z["joint_counts"])
