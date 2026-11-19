"""N03D-G source-bound physical-contact acceptance gate, no claims of real source verification.
All numerical acceptance is narrow, rejects fake passes from no near-contact frames.
"""
import math,re
SCHEMA="scp.n03d-g.evaluated-foot-contact-observer.v1"
SHA=re.compile(r"^[a-f0-9]{64}$")
SIDES=("rest_local_x_negative","rest_local_x_positive")

def require(ok,reason):
 if not ok:raise ValueError(reason)
def valid_sha(x):
 return isinstance(x,str) and SHA.fullmatch(x) is not None and x!="0"*64
def validate(obs):
 require(isinstance(obs,dict) and obs.get("schema")==SCHEMA,"SCHEMA_MISMATCH")
 require(obs.get("source_class")=="ORIGINAL_FICTIONAL_CC0", "SOURCE_RIGHTS_CLASS_REJECTED")
 for k in ("source_scene_sha256","retarget_action_sha256","source_wardrobe_sha256"):
  require(valid_sha(obs.get(k)),"INVALID_SOURCE_SHA_"+k)
 require(obs["source_scene_sha256"]!=obs["source_wardrobe_sha256"],"REUSED_SOURCE_PROVENANCE")
 require(obs.get("frame_rate_hz")==24,"FRAME_RATE_24HZ_REQUIRED")
 require(isinstance(obs.get("actors"),list) and sorted(x.get("actor","") for x in obs["actors"])==["AsterOriginal","JuniperOriginal"],"ACTOR_PAIR_INVALID")
 for actor in obs["actors"]:
  sides=actor.get("sides")
  require(isinstance(sides,dict) and set(sides)==set(SIDES),"SIDE_SET_OR_PARTITIONS_INVALID")
  for name in SIDES:
   samples=sides[name].get("samples")
   require(isinstance(samples,list) and len(samples)>=100 and len(samples)<=300,"SAMPLES_INSUFFICIENT_OR_UNBOUNDED")
   prev=-1
   for p in samples:
    require(set(p)=={"t_s","z_m","xy_m"},"SOURCE_SAMPLE_SHAPE_INVALID")
    t,z,xy=p["t_s"],p["z_m"],p["xy_m"]
    require(type(t) in (float,int) and math.isfinite(t) and t>prev and 0<=t<=6.1,"CLOCK_NOT_MONOTONIC")
    require(prev<0 or .020<=t-prev<=.063,"SUBFRAME_CLOCK_GAP")
    prev=t
    require(type(z) in (float,int) and math.isfinite(z) and -5<z<5,"SHOE_Z_NONFINITE")
    require(isinstance(xy,list) and len(xy)==2 and all(type(v) in (float,int) and math.isfinite(v) and abs(v)<100 for v in xy),"SHOE_XY_NONFINITE")
   require(valid_sha(sides[name].get("shoe_rest_mesh_sha256")),"SHOE_MESH_SOURCE_DRIFT")
 return True

def measure(points,fps=24):
 minz=min(p["z_m"] for p in points)
 maxz=max(p["z_m"] for p in points)
 idx=[i for i,p in enumerate(points) if -0.012<=p["z_m"]<=0.012]
 speeds=[]
 for i in range(1,len(points)):
  a=points[i-1];b=points[i]
  if -0.012<=a["z_m"]<=.012 and -0.012<=b["z_m"]<=.012:
   dt=b["t_s"]-a["t_s"]
   if dt<=0:raise ValueError("NON_POSITIVE_CLOCK")
   speeds.append(math.hypot(b["xy_m"][0]-a["xy_m"][0],b["xy_m"][1]-a["xy_m"][1])/dt)
 return {"minimum_z_m":round(minz,6),"maximum_z_m":round(maxz,6),
  "penetration_m":round(max(0,-minz),6),"near_ground_samples":len(idx),
  "adjacent_contact_speed_pairs":len(speeds),"max_near_ground_slide_mps":round(max(speeds),6) if speeds else None}

def decide(obs):
 validate(obs)
 rows=[];reasons=[]
 for actor in obs["actors"]:
  for side in SIDES:
   obj=actor["sides"][side]
   m=measure(obj["samples"])
   sideReasons=[]
   if m["penetration_m"]>.01:sideReasons.append("PENETRATION_GT_10MM")
   if m["near_ground_samples"]<4 or m["adjacent_contact_speed_pairs"]<3:
    sideReasons.append("UNKNOWN_INSUFFICIENT_CONSECUTIVE_CONTACT")
   if m["max_near_ground_slide_mps"] is None:
    sideReasons.append("UNKNOWN_SLIDING_NOT_OBSERVABLE")
   elif m["max_near_ground_slide_mps"]>.08:sideReasons.append("NEAR_GROUND_SKATING_GT_0P08_MPS")
   if not obj.get("anatomical_side_verified",False):
    sideReasons.append("ANATOMICAL_PARTITION_UNVERIFIED")
   rows.append({"actor":actor["actor"],"partition":side,"numeric":m,
    "reasons":sideReasons})
   reasons.extend(sideReasons)
 if obs.get("independent_visual_review_passed") is not True:
  reasons.append("INDEPENDENT_VISUAL_REVIEW_NOT_PASSED")
 if not obs.get("post_ik_source_rig_verified",False):
  reasons.append("POST_IK_RIG_NOT_VERIFIED")
 if obs.get("root_correction_m") is None:
  reasons.append("UNKNOWN_ROOT_CORRECTION")
 elif type(obs["root_correction_m"]) not in (int,float) or not math.isfinite(obs["root_correction_m"]) or abs(obs["root_correction_m"])>.05:
  reasons.append("EXCESSIVE_ROOT_CORRECTION")
 return {"schema":"scp.n03d-g.contact-admission.v1",
  "status":"HOLD_"+("_".join(sorted(set(reasons))) if reasons else "NONE") if reasons else "PASS_NARROW_NUMERIC_AND_REVIEW_GATES",
  "actors":rows,"fail_reasons":sorted(set(reasons)),
  "contact_metrics_pass_narrow":not reasons,
  "human_naturalness_proven":False,"protected_character_identity_proven":False,
  "mvp_accepted":False,"release_authorized":False}
