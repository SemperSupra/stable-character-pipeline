"""R078 original-fictional MakeHuman Aster/Juniper source intent. No real identities."""
import json,math
SCHEMA="scp.r078.original-mpfb-substitute.v1"
PHENOTYPE_KEYS=("gender","height","weight","muscle","proportions")
UPSTREAM="9de0707fdc88438d7c53a1a2ac7937d9221e2431"
SOURCE_ORIGINAL="5ac608af0440dcd7e61f5e3423b4d52972af29830f9ee24a888178cd4760fcd4"
PROFILES=(
 {"name":"AsterOriginal","gender":0.0,"height":.68,"weight":.35,"muscle":.43,"proportions":.36,"phase":0.0,"skin_color":(.58,.35,.24)},
 {"name":"JuniperOriginal","gender":0.0,"height":.42,"weight":.66,"muscle":.38,"proportions":.40,"phase":.40,"skin_color":(.36,.24,.19)},
)
FPS=12
FRAMES=72
FLOOR_Z=0.0
def require(ok,code):
    if not ok:raise ValueError(code)
def validate_profiles(rows=PROFILES):
    require(isinstance(rows,(list,tuple)) and len(rows)==2,"EXACTLY_TWO_PROFILES_REQUIRED")
    require([r.get("name") for r in rows]==["AsterOriginal","JuniperOriginal"],"ORIGINAL_IDENTITY_KEYS_CHANGED")
    for p in rows:
        require(set(p)=={"name","phase","skin_color",*PHENOTYPE_KEYS},"PROFILE_SCHEMA_UNEXPECTED")
        require(all(type(p[k]) in (int,float) and math.isfinite(p[k]) and 0<=p[k]<=1 for k in PHENOTYPE_KEYS),"MACRO_OUT_OF_ENVELOPE")
        require(type(p["phase"]) in (int,float) and math.isfinite(p["phase"]),"PHASE_NOT_FINITE")
        require(len(p["skin_color"])==3 and all(type(c) in (int,float) and math.isfinite(c) and 0<=c<=1 for c in p["skin_color"]),"SKIN_COLOR_OUT_OF_ENVELOPE")
    require(any(abs(rows[0][s]-rows[1][s])>.1 for s in ("height","weight","muscle","proportions")),"SUBSTITUTE_BODIES_NOT_DISTINCT")
    return True
def source_centers(frame):
    require(type(frame) is int and 0<=frame<FRAMES,"FRAME_OUT_OF_RANGE")
    progress=frame/(FRAMES-1)
    return (-3.35+2.56*progress,3.35-2.56*progress)
def validate_shape_metrics(m):
    require(isinstance(m,dict),"SHAPE_METRICS_MISSING")
    require(set(m)=={"bbox_x_over_height","bbox_y_over_height","leg_segments","measured_from","anatomical_landmark_centres_accepted"},"SHAPE_METRICS_SCHEMA_DRIFT")
    require(m["measured_from"]=="EVALUATED_SAVED_MPF_BODY_AND_NATIVE_REST_RIG","NON_NATIVE_GEOMETRY_FIT")
    require(m["anatomical_landmark_centres_accepted"] is False,"FALSE_ANATOMY_ACCEPTANCE")
    require(all(type(m[k]) in (int,float) and math.isfinite(m[k]) and 0<m[k]<10 for k in ("bbox_x_over_height","bbox_y_over_height")),"INVALID_BODY_METRIC")
    leg=m["leg_segments"]
    require(isinstance(leg,dict) and set(leg)=={"upper_L_over_height","upper_R_over_height","lower_L_over_height","lower_R_over_height"},"LEG_SEGMENT_KEYS_DRIFT")
    require(all(type(v) in (int,float) and math.isfinite(v) and 0<v<10 for v in leg.values()),"INVALID_LEG_METRIC")
    return True
def validate_receipt(r):
    require(r.get("schema")==SCHEMA,"WRONG_SCHEMA")
    require(r.get("source_class")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0","NOT_SOURCE_SAFE")
    require(r.get("mpfb_upstream_commit")==UPSTREAM,"UPSTREAM_NOT_PINNED")
    require(r.get("fps")==FPS and r.get("frames")==FRAMES,"SOURCE_TIMEBASE_CHANGED")
    require([x["name"] for x in r["actors"]]==[x["name"] for x in PROFILES],"SOURCE_ACTOR_NAMES_DRIFT")
    require(all(x["bones"]>=100 and x["body_vertices"]>10000 for x in r["actors"]),"NOT_REAL_MPF_FRONTEND_RIG")
    require(all(x["rest_pose_sha256"]!=x["mid_pose_sha256"] for x in r["actors"]),"NOT_DEFORMING_REAL_MPF_BODIES")
    require(all(validate_shape_metrics(x.get("native_body_shape_metrics")) for x in r["actors"]),"NOT_MEASURED_ACTOR_SHAPES")
    require(all(not r.get(k,True) for k in ("photoreal_accepted","gait_accepted","real_identity_accepted","mvp_accepted","release_authorized")),"FALSE_PRODUCT_ACCEPTANCE")
    return True
