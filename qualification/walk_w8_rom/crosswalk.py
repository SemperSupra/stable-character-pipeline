"""Independent W7 native six-bone ↔ source joint ROM mathematical witness.

No biological JCS, source-leg symmetry, energy, torque, loading or person claim.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
ACTORS=("CobaltOriginal","MarigoldOriginal")
LEGS=("Left","Right")
TOL=.001
FRAMES=24
FPS=12

def require(ok,code):
    if not ok:raise ValueError(code)

def vec(x,code):
    require(isinstance(x,list) and len(x)==3 and
            all(type(v) in (float,int) and math.isfinite(v) for v in x),code)
    return x

def flexion(hip,knee,ankle):
    a=[hip[i]-knee[i] for i in range(3)]
    b=[ankle[i]-knee[i] for i in range(3)]
    la=math.sqrt(sum(v*v for v in a));lb=math.sqrt(sum(v*v for v in b))
    require(la>.01 and lb>.01,"W8_DEGENERATE_BONE")
    c=max(-1.0,min(1.0,sum(a[i]*b[i] for i in range(3))/(la*lb)))
    return math.pi-math.acos(c)

def audit(source_raw,receipt,native,sole):
    source=json.loads(source_raw)
    require(source.get("schema")=="scp.walk_w7a_original_approach.v1" and
            source.get("rights")==RIGHTS and
            source.get("scenario")=="ORIGINAL_2ACTOR_WORLD_X_APPROACH_NOT_HUMAN_GAIT",
            "W8_SOURCE_SCENARIO_RIGHTS")
    require(source.get("fps_num")==FPS and len(source.get("actors",[]))==2,
            "W8_SOURCE_PROFILE_CLOCK")
    sh=hashlib.sha256(source_raw).hexdigest()
    require(receipt.get("source_sha256")==sh and native.get("source_sha256")==sh and
            receipt.get("blend_sha256")==native.get("blend_sha256") and
            native.get("schema")=="scp.walk_w8_native_sixbone_joint_observation.v1",
            "W8_SOURCE_NATIVE_IMMUTABLE_SHA")
    require(receipt.get("rights")==RIGHTS and receipt.get("frame_count")==FRAMES and
            native.get("rights")==RIGHTS and native.get("fps")==FPS and
            native.get("profile")==source.get("profile") and
            native.get("native_evaluation")=="ACTUAL_BLENDER_EVALUATED_ARMATURE_NOT_BIOLOGICAL",
            "W8_NATIVE_UNAUTHORIZED_OR_CLOCK")
    require(len(native.get("observations",[]))==FRAMES and len(sole)==FRAMES,
            "W8_FRAME_COVERAGE")
    maxerr=0.
    angles={a:{leg:[] for leg in LEGS} for a in ACTORS}
    roots=[[],[]]
    max_footerr=0.
    for t in range(FRAMES):
        observed=native["observations"][t]
        so=sole[t]
        require(observed.get("tick")==t and so.get("frame")==t and
                len(observed.get("actors",[]))==2 and len(so.get("actors",[]))==2,
                "W8_TICK_OR_ACTOR_COVERAGE")
        for ai,actor in enumerate(ACTORS):
            srca=source["actors"][ai]
            sf=srca["frames"][t]
            na=observed["actors"][ai]
            foota=so["actors"][ai]
            require(srca.get("id")==actor and na.get("id")==actor and
                    foota.get("name")==actor and na.get("bones")==6 and
                    len(na.get("legs",[]))==2 and len(foota.get("legs",[]))==2 and
                    sf.get("index")==t and sf.get("time_num")==t and
                    sf.get("time_den")==FPS,"W8_SIX_BONE_ID_OR_EXACT_CLOCK")
            root=sf.get("root_x")
            require(type(root) in (int,float) and math.isfinite(root),"W8_NONFINITE_ROOT")
            roots[ai].append(root)
            for li,leg in enumerate(LEGS):
                sl=sf["legs"][li];nl=na["legs"][li];fl=foota["legs"][li]
                require(sl.get("id")==nl.get("id")==fl.get("id")==leg and
                        nl.get("leg_bone_count")==3 and
                        fl.get("state")==sl.get("state"),
                        "W8_LEG_ID_OR_CONTACT_LABEL")
                for part in ("hip","knee","ankle"):
                    p=vec(nl.get(part),"W8_UNOBSERVED_OR_NONFINITE_JOINT")
                    q=vec(sl.get(part),"W8_SOURCE_BAD_JOINT")
                    err=math.dist(p,q);maxerr=max(maxerr,err)
                    require(err<=TOL,"W8_EVALUATED_SOURCE_JOINT_MISMATCH")
                for part in ("foot_head","foot_tail"):
                    vec(nl.get(part),"W8_MISSING_NATIVE_FOOT_BONE")
                lh=math.dist(nl["hip"],nl["knee"])
                ls=math.dist(nl["knee"],nl["ankle"])
                require(abs(lh-.6)<TOL and abs(ls-.6)<TOL,
                        "W8_MECHANICAL_SEGMENT_LENGTH")
                for part in ("heel","toe"):
                    p=vec(fl.get(part),"W8_UNOBSERVED_NATIVE_FOOT")
                    q=vec(sl.get(part),"W8_BAD_SOURCE_FOOT")
                    e=math.dist(p,q);max_footerr=max(e,max_footerr)
                    require(e<=TOL,"W8_SOURCE_NATIVE_FOOT_MISMATCH")
                angles[actor][leg].append(flexion(nl["hip"],nl["knee"],nl["ankle"]))
    require(roots[0][-1]>roots[0][0] and roots[1][-1]<roots[1][0],
            "W8_NOT_APPROACHING")
    for t in range(FRAMES-1):
        require((roots[1][t+1]-roots[0][t+1])<
                (roots[1][t]-roots[0][t]),"W8_NONMONOTONE_APPROACH")
    observed_ranges={}
    for actor in ACTORS:
        observed_ranges[actor]={}
        for leg in LEGS:
            theta=angles[actor][leg]
            rates=[(theta[i]-theta[i-1])*FPS for i in range(1,FRAMES)]
            acceleration=[(rates[i]-rates[i-1])*FPS for i in range(1,len(rates))]
            jerk=[(acceleration[i]-acceleration[i-1])*FPS for i in range(1,len(acceleration))]
            observed_ranges[actor][leg]={
                "mathematical_flexion_rad_min":min(theta),
                "mathematical_flexion_rad_max":max(theta),
                "max_abs_angular_velocity_rad_s":max(map(abs,rates)),
                "max_abs_angular_acceleration_rad_s2":max(map(abs,acceleration)),
                "max_abs_angular_jerk_rad_s3":max(map(abs,jerk)),
                "biological_rom":"UNKNOWN_NO_SOURCE_APPROVED_HUMAN_JCS"}
    return {"schema":"scp.walk_w8_exact_native_sixbone_rom_crosswalk.v1",
            "status":"PASS_SYNTHETIC_NATIVE_SOURCE_KINEMATICS_ONLY",
            "source_sha256":sh,"blend_sha256":native["blend_sha256"],
            "profile":source["profile"],"frames":FRAMES,"fps":FPS,
            "actors":2,"observed_bones_per_actor":6,
            "max_evaluated_joint_position_error":maxerr,
            "max_evaluated_heel_toe_error":max_footerr,
            "source_actor_separation_start":roots[1][0]-roots[0][0],
            "source_actor_separation_end":roots[1][-1]-roots[0][-1],
            "observed_mathematical_rom":observed_ranges,
            "biological_jcs":"UNKNOWN_NO_SOURCE_APPROVED_ANATOMICAL_FRAME",
            "physical_loading":"UNKNOWN_NO_FORCE_TORQUE_OR_BODY_MASS",
            "full_body_human":"UNKNOWN_NOT_OBSERVED",
            "R009_product":"HELD","CPE_promotion":"HELD",
            "rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("folder");p.add_argument("receipt")
    a=p.parse_args();folder=Path(a.folder)
    try:
        result=audit((folder/"source.json").read_bytes(),
                json.loads((folder/"source_motion_receipt.json").read_text()),
                json.loads((folder/"native_sixbone_joint_24frame.json").read_text()),
                json.loads((folder/"evaluated_sole_24frame.json").read_text()))
        Path(a.receipt).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        print("W8_SIX_BONE_NATIVE_ROM_MATH_PASS",result["profile"],result["source_sha256"])
    except (ValueError,KeyError,TypeError,IndexError,OSError,json.JSONDecodeError) as err:
        Path(a.receipt).write_text(json.dumps({"status":"FAIL","first_failure":str(err),
                 "schema":"scp.walk_w8_exact_native_sixbone_rom_crosswalk.v1",
                 "no_biological_or_R009_promotion":True},sort_keys=True,indent=2)+"\n")
        raise SystemExit("W8_SIX_BONE_ROM_FIRST_FAILURE "+str(err))

if __name__=="__main__":main()
