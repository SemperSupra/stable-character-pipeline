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
# 4.5.16 LTS same-source baseline from R090 PR #656 head d12dd29a5e450,
# official free public GHA #44267274270. Values are public original-fictional metadata.
BASELINE_R090_45={
 "AsterOriginal":{
  "rest_local_x_negative":(.072160,.095578,None,None,2,5,("PENETRATION_OVER_10MM","NO_TWO_CONSECUTIVE_CONTACT_SAMPLES")),
  "rest_local_x_positive":(.072160,.089501,None,1.516302,4,7,("PENETRATION_OVER_10MM","PLANTED_FOOT_SLIDING"))},
 "JuniperOriginal":{
  "rest_local_x_negative":(.029447,.020216,1.138464,2.638501,25,41,("PENETRATION_OVER_10MM","PLANTED_FOOT_SLIDING")),
  "rest_local_x_positive":(.029447,.017051,1.127806,2.962075,23,39,("PENETRATION_OVER_10MM","PLANTED_FOOT_SLIDING"))}}
def compare_with_45(cmp):
 if not isinstance(cmp,dict) or sorted(x["actor"] for x in cmp.get("actors",[]))!=sorted(BASELINE_R090_45):
  raise ValueError("REFERENCE_ACTOR_SET_DRIFT")
 largest_penetration=0.
 largest_slip=0.
 for actor in cmp["actors"]:
  name=actor["actor"]
  if len(actor["feet"])!=2:raise ValueError("SYNTHETIC_SHOE_PAIR_DRIFT")
  seen=set()
  for foot in actor["feet"]:
   side=foot["side_partition_static_rest_local_x"]
   if side not in BASELINE_R090_45[name] or side in seen:raise ValueError("FOOT_INDEX_LINEAGE_DRIFT")
   seen.add(side)
   ap,rp,asl,rsl,af,rf,flags=BASELINE_R090_45[name][side]
   if af!=foot["authored_near_ground_frames"] or rf!=foot["recorded_near_ground_frames"]:
    raise ValueError("CONTACT_FRAME_DRIFT")
   if tuple(foot["recorded_flags"])!=flags:raise ValueError("CONTACT_DIAGNOSTIC_FLAG_DRIFT")
   for key,prior in (("authored_penetration_m",ap),("recorded_penetration_m",rp)):
    value=foot[key]
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
     raise ValueError("INVALID_PENETRATION_NUMERIC")
    delta=abs(float(value)-prior)
    largest_penetration=max(largest_penetration,delta)
    if delta>2e-5:raise ValueError("BLENDER_NATIVE_SOLE_PARITY_RED")
   for key,prior in (("authored_slip_mps",asl),("recorded_slip_mps",rsl)):
    value=foot[key]
    if prior is None:
     if value is not None:raise ValueError("FALSE_SLIP_OBSERVATION")
    else:
     if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
      raise ValueError("INVALID_SLIP_NUMERIC")
     delta=abs(float(value)-prior)
     largest_slip=max(largest_slip,delta)
     if delta>2e-4:raise ValueError("BLENDER_NATIVE_SLIP_PARITY_RED")
 return {"baseline_blender":"4.5.16 LTS","baseline_github_run":44267274270,
         "penetration_max_abs_delta_m":largest_penetration,
         "sliding_max_abs_delta_mps":largest_slip,"source_aware_contact_parity":True,
         "contact_or_gait_accepted":False}

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
 check("COMPARISON_SCHEMA",isinstance(cmp,dict) and cmp.get("schema")=="scp.r090.measured-sole-gait-bakeoff.v1")
 check("COMPARISON_ACTORS",sorted(a["actor"] for a in cmp.get("actors",[]))==["AsterOriginal","JuniperOriginal"])
 check("COMPARISON_NOT_GAIT_ACCEPTED",cmp.get("admission")=="MEASURED_CONTACT_DIAGNOSTIC_NOT_GAIT_ACCEPTED"
       and cmp.get("natural_gait_accepted") is False and cmp.get("mvp_accepted") is False
       and cmp.get("visual_critic_passed") is False)
 reference=compare_with_45(cmp)
 return {"schema":"scp.blender5x.mpfb-retarget-admission.v1",
         "source_blender_expected":version,"recorded_compared_to_same-version_authored":True,
         "4_5_16_reference":reference,
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
