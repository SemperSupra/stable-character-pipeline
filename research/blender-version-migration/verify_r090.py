"""Independent source/clock/rights and numeric evidence receipt across Blender LTS/stable.
No identity, cloth or gait quality is accepted by this verifier.
"""
import hashlib,json,math,sys
from pathlib import Path

def load(path):
 raw=Path(path).read_bytes()
 if len(raw)>1_000_000:raise ValueError("OVERSIZED_JSON")
 d=json.loads(raw)
 return d,hashlib.sha256(raw).hexdigest()
def check(name,condition):
 if not condition:raise ValueError(name)
def run(paths):
 auth,ah=load(paths[0]);rec,rh=load(paths[1]);cmp,ch=load(paths[2])
 version=paths[3]
 check("BLENDER_VERSION_UNSUPPORTED",version in ("5.2.4","5.3.0"))
 check("AUTHORED_SCHEMA",auth.get("schema")=="scp.r090.72f-real-shoe-contact.v1")
 check("RECORDED_SCHEMA",rec.get("schema")=="scp.r090.72f-real-shoe-contact.v1")
 check("WRONG_MODES",auth.get("mode")=="authored" and rec.get("mode")=="recorded")
 check("CLOCK",auth.get("fps")==rec.get("fps")==12 and auth.get("frames")==rec.get("frames")==72)
 check("SOURCE_JOIN",auth.get("scene_sha256")==rec.get("wardrobe_base_sha256"))
 check("UNSUPPORTED_SOURCE",auth.get("source_origin")==rec.get("source_origin")=="ORIGINAL_FICTIONAL_AND_SOURCE_RIGHTS_PINNED")
 for scene in (auth,rec):
  check("INVALID_ACTORS",sorted(a["actor"] for a in scene["actors"])==["AsterOriginal","JuniperOriginal"])
  check("UNVERIFIED_CONTACT",scene.get("gait_accepted") is False and scene.get("physical_contact_accepted") is False and scene.get("mvp_accepted") is False)
  for a in scene["actors"]:
   feet=a["rest_local_x_partitions"]
   check("SIDE_COUNT",len(feet)==2 and set(feet)=={"rest_local_x_negative","rest_local_x_positive"})
   check("SIDE_SEMANTIC",a["anatomical_side_verified"] is False)
   for value in feet.values():
    check("INVALID_SAMPLES",value.get("samples")==72 and value.get("gait_contact_accepted") is False)
    for key in ("penetration_m","minimum_z_m","maximum_z_m"):
     check("NONFINITE_GEOMETRY",isinstance(value.get(key),(float,int)) and math.isfinite(value[key]))
 check("COMPARISON_NOT_JSON",not isinstance(cmp,dict))
 # Comparison schema may evolve. Its presence and bytes are recorded, but it never issues release authority.
 return {"schema":"scp.blender5x.mpfb-retarget-admission.v1",
         "source_blender_expected":version,"recorded_compared_to_same-version_authored":True,
         "authored_sha256":ah,"recorded_sha256":rh,"comparison_sha256":ch,
         "actor_count":2,"frames":72,"fps":12,"rights_scope":"ORIGINAL_FICTIONAL_AND_SOURCE_RIGHTS_PINNED",
         "status":"PASS_NARROW_NATIVE_SOURCE_PARITY_HOLD_CONTACT",
         "source_identity_accepted":False,"foot_contact_accepted":False,
         "blender_5x_production_promoted":False,"mvp_accepted":False,"release_authorized":False}
if __name__=="__main__":
 try:print(json.dumps(run(sys.argv[1:]),sort_keys=True,allow_nan=False))
 except (OSError,ValueError,TypeError,KeyError) as e:
  print("SCP_VERSION_GATE_RED",repr(e),file=sys.stderr)
  sys.exit(12)
