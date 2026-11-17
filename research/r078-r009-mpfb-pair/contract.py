"""R078 original-fictional MakeHuman Aster/Juniper source intent. No real identities."""
import json,math
SCHEMA="scp.r078.original-mpfb-substitute.v1"
UPSTREAM="9de0707fdc88438d7c53a1a2ac7937d9221e2431"
SOURCE_ORIGINAL="5ac608af0440dcd7e61f5e3423b4d52972af29830f9ee24a888178cd4760fcd4"
PROFILES=(
 {"name":"AsterOriginal","height":.68,"weight":.35,"phase":0.0,"skin_color":(.58,.35,.24)},
 {"name":"JuniperOriginal","height":.42,"weight":.66,"phase":.40,"skin_color":(.36,.24,.19)},
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
        require(set(p)=={"name","height","weight","phase","skin_color"},"PROFILE_SCHEMA_UNEXPECTED")
        require(all(type(p[k]) in (int,float) and math.isfinite(p[k]) and 0<=p[k]<=1 for k in ("height","weight")),"MACRO_OUT_OF_ENVELOPE")
        require(type(p["phase"]) in (int,float) and math.isfinite(p["phase"]),"PHASE_NOT_FINITE")
        require(len(p["skin_color"])==3 and all(type(c) in (int,float) and math.isfinite(c) and 0<=c<=1 for c in p["skin_color"]),"SKIN_COLOR_OUT_OF_ENVELOPE")
    require(any(abs(rows[0][s]-rows[1][s])>.1 for s in ("height","weight")),"SUBSTITUTE_BODIES_NOT_DISTINCT")
    return True
def source_centers(frame):
    require(type(frame) is int and 0<=frame<FRAMES,"FRAME_OUT_OF_RANGE")
    progress=frame/(FRAMES-1)
    return (-3.35+2.56*progress,3.35-2.56*progress)
def validate_receipt(r):
    require(r.get("schema")==SCHEMA,"WRONG_SCHEMA")
    require(r.get("source_class")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0","NOT_SOURCE_SAFE")
    require(r.get("mpfb_upstream_commit")==UPSTREAM,"UPSTREAM_NOT_PINNED")
    require(r.get("fps")==FPS and r.get("frames")==FRAMES,"SOURCE_TIMEBASE_CHANGED")
    require([x["name"] for x in r["actors"]]==[x["name"] for x in PROFILES],"SOURCE_ACTOR_NAMES_DRIFT")
    require(all(x["bones"]>=100 and x["body_vertices"]>10000 for x in r["actors"]),"NOT_REAL_MPF_FRONTEND_RIG")
    require(all(x["rest_pose_sha256"]!=x["mid_pose_sha256"] for x in r["actors"]),"NOT_DEFORMING_REAL_MPF_BODIES")
    require(all(not r.get(k,True) for k in ("photoreal_accepted","gait_accepted","real_identity_accepted","mvp_accepted","release_authorized")),"FALSE_PRODUCT_ACCEPTANCE")
    return True
