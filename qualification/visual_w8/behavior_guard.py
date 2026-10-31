"""W8 independent full-image QA admission guard for original unannotated videos.

Positive upper-body source kinematics != normative/biological human behavior.
This keeps unchanged W7/W6 frozen L1 and honest scientific FAIL/UNKNOWN.
"""
import argparse, hashlib, json, math
from pathlib import Path

RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
CAMERAS=("OriginalFront","OriginalOblique")
ACTORS=("CobaltOriginal","MarigoldOriginal")
SIDES=("Left","Right")
SHA_DIGITS="0123456789abcdef"

def require(ok,code):
    if not ok:raise ValueError(code)
def digest(b):return hashlib.sha256(b).hexdigest()
def finite(x):return type(x) in (float,int) and math.isfinite(x)
def audit(original_source_raw,native_source,render,upper,rollup,views):
    source=json.loads(original_source_raw)
    sh=digest(original_source_raw)
    require(source.get("schema")=="scp.walk_w7a_original_approach.v1" and
            source.get("rights")==RIGHTS and source.get("fps_num")==12,
            "W8_VIS_SOURCE_RIGHTS_OR_CLOCK")
    require(native_source.get("source_sha256")==sh and
            render.get("source_motion_sha256")==sh and
            upper.get("source_motion_sha256")==sh and
            rollup.get("source_motion_sha256")==sh,
            "W8_VIS_ORIGINAL_SOURCE_DIGEST_DISAGREEMENT")
    require(native_source.get("blend_sha256")==render.get("original_w5d_blend_sha256")==
            upper.get("original_blend_sha256")==rollup.get("source_blend_sha256"),
            "W8_VIS_ORIGINAL_BLEND_CUSTODY_MISMATCH")
    require(native_source.get("rights")==render.get("rights")==RIGHTS and
            render.get("schema")=="scp.walk_w6a_proxy_multiview.v1" and
            upper.get("schema")=="scp.walk_w8a_observed_upper_proxy.v1",
            "W8_VIS_WRONG_RENDER_OR_RIGHTS")
    require(render.get("W8_arm_motion")=="ACTUAL_KEYED_RIGID_UPPER_PROXY_24FRAME" and
            render.get("torso_arm_skinning")=="NOT_DEFORM_RIGGED" and
            render.get("natural_human_behavior")=="UNKNOWN_NO_INDEPENDENT_NORMATIVE_MODEL",
            "W8_VIS_FALSE_NATURAL_HUMAN_PROMOTION")
    samples=upper.get("frames",[])
    require(len(samples)==24,"W8_VIS_NATIVE_24_FRAMES_REQUIRED")
    maxangle=0.
    for t,frame in enumerate(samples):
        require(frame.get("frame")==t and len(frame.get("actors",[]))==2,
                "W8_VIS_NATIVE_UPPER_FRAME_CLOCK")
        for ai,actor in enumerate(frame["actors"]):
            require(actor.get("id")==ACTORS[ai] and len(actor.get("arms",[]))==2,
                    "W8_VIS_NATIVE_UPPER_ARM_SET")
            for li,arm in enumerate(actor["arms"]):
                side=SIDES[li];sign=1 if li==0 else -1
                expect=.28*math.sin(2*math.pi*t/12)*sign
                hand=.20*math.sin(2*math.pi*t/12)*sign
                angle=arm.get("upper_arm_x_rad")
                require(arm.get("side")==side and finite(angle) and
                        finite(arm.get("hand_local_y")),
                        "W8_VIS_NONFINITE_OR_WRONG_ARM_ID")
                require(abs(angle-expect)<1e-5 and abs(arm["hand_local_y"]-hand)<1e-5,
                        "W8_VIS_NATIVE_ARM_NOT_AUTHORED_MOTION")
                maxangle=max(maxangle,abs(angle))
    require(maxangle>.25,"W8_VIS_ACTUAL_ARMS_STATIC")
    cameras=render.get("cameras",[])
    checks=rollup.get("cameras",[])
    require(len(cameras)==len(checks)==2 and
            {x.get("camera") for x in cameras}==set(CAMERAS) and
            {x.get("camera") for x in checks}==set(CAMERAS),
            "W8_VIS_BOTH_REQUIRED_CAMERAS")
    require(set(views)==set(CAMERAS),"W8_VIS_MISSING_REQUIRED_VIDEO")
    results=[];some_red=False
    for cam in CAMERAS:
        item=next(x for x in cameras if x["camera"]==cam)
        check=next(x for x in checks if x["camera"]==cam)
        vid=views[cam]["video"];qa=views[cam]["qa"]
        require(type(vid) is bytes and len(vid)>1024,
                "W8_VIS_NOT_ACTUAL_UNANNOTATED_VIDEO_BYTES")
        vh=digest(vid)
        require(item["video_sha256"]==check.get("video_sha256")==qa.get("source_sha256")==vh,
                "W8_VIS_DIFFERENT_VIDEO_ACROSS_OBSERVERS")
        require(qa.get("schema")=="scp.visualqa.l1_video.v1" and
                qa.get("frames_decoded")==24 and qa.get("video",{}).get("rate")=="12/1",
                "W8_VIS_NOT_ACTUAL_24F_DECODED_VIDEO")
        status=qa.get("status")
        require(status in ("PASS_L1_VIDEO_ONLY","FAIL") and status==check.get("status"),
                "W8_VIS_L1_STATUS_CROSSWALK")
        require((status=="FAIL" and len(qa.get("failures",[]))>0) or
                (status=="PASS_L1_VIDEO_ONLY" and not qa.get("failures",[])),
                "W8_VIS_FALSE_L1_VERDICT")
        if status=="FAIL":some_red=True
        results.append({"camera":cam,"same_clean_video_sha256":vh,
                        "frozen_L1_observed_status":status,
                        "frozen_L1_first_failure":qa.get("failures",[])})
    expected="FAIL_L1_ANY_REQUIRED_VIEW" if some_red else "PASS_ALL_REQUIRED_VIEWS_L1_ONLY"
    require(rollup.get("status")==expected and
            render.get("profile")==rollup.get("profile")==source.get("profile"),
            "W8_VIS_ROLLUP_OR_PROFILE_FALSIFIED")
    return {"schema":"scp.visualqa.w8_actual_original_upperbody_guard.v1",
            "status":"FAIL_L1_AND_FULLBODY_PROXY_UNQUALIFIED" if some_red else
                     "FAIL_FULLBODY_HUMAN_BEHAVIOR_PROXY_UNQUALIFIED",
            "source_sha256":sh,"blend_sha256":native_source["blend_sha256"],
            "profile":source["profile"],"video_views":results,
            "source_arm_motion":"PASS_ACTUAL_BLENDER_RIGID_UPPER_PROXY_ONLY",
            "max_observed_synthetic_arm_rotation_rad":maxangle,
            "original_video_L1":"FAIL" if some_red else "PASS_VIDEO_ONLY",
            "normative_anatomy_and_gait":"UNKNOWN_NO_INDEPENDENT_HUMAN_SPECIES_JCS_OR_PRIOR",
            "independent_vision_video_behavior_critic":"NOT_RUN_NO_ADMITTED_MODEL",
            "full_body_behavior":"FAIL_STATIC_TORSO_AND_NONSKINNED_PROXY_GEOMETRY",
            "source_to_video_fidelity":"PARTIAL_ONLY_SOURCE_SHA_PLUS_FROZEN_L1",
            "naturalness_acceptance":"NO",
            "real_person_R009":"HELD","rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "no_public_person_identity_or_biometric_source":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("folder");p.add_argument("out")
    x=p.parse_args();root=Path(x.folder)
    try:
        source=(root/"source.json").read_bytes()
        native=json.loads((root/"source_motion_receipt.json").read_text())
        render=json.loads((root/"rendered/native_render_receipt.json").read_text())
        upper=json.loads((root/"rendered/observed_blender_upper_arm_24frame.json").read_text())
        rollup=json.loads((root/"rendered/independent_cross_camera_rollup.json").read_text())
        views={}
        for cam in CAMERAS:
            r=root/"rendered"
            views[cam]={"video":(r/(cam+".mp4")).read_bytes(),
                  "qa":json.loads((r/("qa-"+cam)/"video_qa.json").read_text())}
        result=audit(source,native,render,upper,rollup,views)
        Path(x.out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        print("W8_VISUAL_BEHAVIOR_GUARD_FAIL_CLOSED",result["status"],result["profile"])
    except (ValueError,KeyError,TypeError,IndexError,OSError,json.JSONDecodeError) as e:
        Path(x.out).write_text(json.dumps({"schema":"scp.visualqa.w8_actual_original_upperbody_guard.v1",
            "status":"UNKNOWN_INVALID_EVIDENCE","first_failure":str(e),
            "no_human_or_R009_promotion":True},sort_keys=True,indent=2)+"\n")
        raise SystemExit("W8_VISUAL_FIRST_FAILURE "+str(e))

if __name__=="__main__":main()
