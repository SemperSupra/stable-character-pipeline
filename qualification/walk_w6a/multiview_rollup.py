"""W6A independent cross-camera, same-immutable-video evidence aggregate.

Both front and oblique are required for the limited L1 verdict. A single
passing view never overrides a failing one. This is not a human image model.
"""
import hashlib,json
from pathlib import Path

RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
CAMERAS=("OriginalFront","OriginalOblique")
def verify(folder):
    folder=Path(folder)
    source=json.loads((folder/"native_render_receipt.json").read_text())
    if source.get("schema")!="scp.walk_w6a_proxy_multiview.v1" or source.get("rights")!=RIGHTS:
        raise ValueError("RENDER_SOURCE_SCHEMA_OR_RIGHTS")
    cameras=source.get("cameras")
    if not isinstance(cameras,list) or len(cameras)!=2 or {x.get("camera") for x in cameras}!=set(CAMERAS):
        raise ValueError("TWO_CAMERA_SOURCE_SET_REQUIRED")
    checks=[];unknown=0;fail=0
    for item in cameras:
        cam=item["camera"]
        video=(folder/(cam+".mp4"))
        if not video.is_file() or hashlib.sha256(video.read_bytes()).hexdigest()!=item["video_sha256"]:
            raise ValueError("ORIGINAL_VIDEO_CONTENT_HASH_MISMATCH")
        qa=(folder/("qa-"+cam)/"video_qa.json")
        if not qa.is_file():
            raise ValueError("INDEPENDENT_L1_RECEIPT_MISSING")
        test=json.loads(qa.read_text())
        if (test.get("schema")!="scp.visualqa.l1_video.v1" or
            test.get("source_sha256")!=item["video_sha256"] or
            test.get("frames_decoded")!=24 or
            test.get("video",{}).get("rate")!="12/1"):
            raise ValueError("L1_SOURCE_VIDEO_OR_TIMECLOCK_DISAGREEMENT")
        status=test.get("status")
        if status=="FAIL":
            fail+=1
            if not test.get("failures"):raise ValueError("L1_FALSE_FAILURE_NO_REASON")
        elif status=="PASS_L1_VIDEO_ONLY":
            if test.get("failures"):raise ValueError("L1_FALSE_PASS_WITH_REASONS")
        else:
            unknown+=1
        checks.append({"camera":cam,"video_sha256":item["video_sha256"],
                       "status":status,"failures":test.get("failures",[]),
                       "unique_decoded_frame_digests":test.get("unique_image_frame_digests")})
    verdict="FAIL_L1_ANY_REQUIRED_VIEW" if fail else ("UNKNOWN_L1_INCOMPLETE" if unknown else "PASS_ALL_REQUIRED_VIEWS_L1_ONLY")
    return {"schema":"scp.walk_w6a_multiview_rollup.v1","status":verdict,
            "profile":source["profile"],"source_motion_sha256":source["source_motion_sha256"],
            "source_blend_sha256":source["original_w5d_blend_sha256"],
            "cameras":checks,"required_view_count":2,
            "human_anatomy":"UNKNOWN_SOURCE_PROXY_ONLY",
            "pixel_inferred_person_pose":"UNKNOWN_NO_MODEL",
            "full_body_skeletal_rig":"UNKNOWN_STATIC_PARENTED_PROXIES",
            "physical_gait":"UNKNOWN_NO_BIOLOGICAL_ROM"}
def main(folder):
    folder=Path(folder)
    r=verify(folder)
    (folder/"independent_cross_camera_rollup.json").write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    # Hard negative check: replace video SHA in the *render source* without
    # changing the actual file or L1 receipt; the join must reject it.
    original=json.loads((folder/"native_render_receipt.json").read_text())
    original["cameras"][0]["video_sha256"]="0"*64
    temp=folder/"native_render_receipt.json"
    origdata=temp.read_bytes()
    try:
        temp.write_text(json.dumps(original))
        try:verify(folder)
        except ValueError as e:
            if str(e)!="ORIGINAL_VIDEO_CONTENT_HASH_MISMATCH":raise
        else:raise ValueError("TAMPERED_MULTI_CAMERA_SOURCE_FALSE_PASS")
    finally:
        temp.write_bytes(origdata)
    print("W6A_INDEPENDENT_MULTI_CAMERA_VERDICT",json.dumps(r,sort_keys=True))
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--folder",required=True)
    main(p.parse_args().folder)
