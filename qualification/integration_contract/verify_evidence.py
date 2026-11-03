#!/usr/bin/env python3
"""R009 three-audience integration receipt gateway, source only.

Reads four *actual* native/observer receipts and three encoded media files,
then writes one fail-closed small typed evidence projection. Never promotes the
protected person/release/CPE even when every synthetic engineering lane passes.
Run with --capabilities for read-only agent DX. No network, secrets or deploy.
"""
import argparse,hashlib,json,math,pathlib,sys
SCHEMA="scp.r009.synthetic-integrated-evidence.v1"
EXPECTED={
 "trace":"1e56d63873b83dc33ea8f510932d1df0e09acfc66e9dae8880f2ae91658d5e86",
 "hier":"03a81c2a5ad6729f3022f4b1d4afbb94395c3a2b29b413ba601480c6995d463a",
 "vmdsource":"ab3a0d712c9c4f21fba0cf0698568dd5f88f1b959cf8aae28173c6435153d760",
 "vmd":"c24f86c00a9d2bae34e1b3928232aa2f6af976ae8169dfbcdbe8c33d6a235409"
}
DONORS={
 "shadow":"4ed129a9234f18145d8bdacac19032df3202716d",
 "bvh":"e2184d09d3a35e8359c34810c53d74af83ccea86",
 "vmd_native":"7f891612a708df13b6f161d1361ebba81b0c38c5",
 "hier":"62937340a789e20d9466fe6ac3feaedb54488f49",
 "visual":"ec584628b31f7765e8e4b985765dc0ff5e914efc",
 "encoded_negative":"7318dcc3036c8ced3a8557bfde5510e8ffe4fb73",
 "debug":"0d0748e3b785bb7bc07417d550b77ac58088866c"
}
class Reject(ValueError):pass
def require(ok,code):
    if not ok:raise Reject(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(name):
    return json.loads(pathlib.Path(name).read_bytes())
def check(native,visual,foot,crosswalk,media,direct_heads,negative):
    require(set(direct_heads)==set(DONORS),"DONOR_ROSTER")
    require(direct_heads==DONORS,"MUTABLE_OR_UNQUALIFIED_DONOR_HEAD")
    require(native.get("schema")=="scp.r009.original-synthetic-integrated-native-park.v1","NOT_ACTUAL_COMPOSED_NATIVE_RECEIPT")
    require(native.get("status")=="PASS_COMPOSED_ORIGINAL_SYNTHETIC_SOURCE_VMD_CALIBRATION_HIER_SKIN_AND_TWO_CAMERA","NATIVE_COMPOSITION_NOT_VERIFIED")
    require(native.get("original_source_sha256")==EXPECTED["trace"],"WRONG_SHADOW_SOURCE")
    require(native.get("hier_source_sha256")==EXPECTED["hier"],"WRONG_HIER_SOURCE")
    require(native.get("vmd_source_sha256")==EXPECTED["vmd"],"WRONG_VMD_SOURCE")
    require(native.get("source_fk_sha256")==crosswalk.get("fk_receipt_sha256"),"FK_RECEIPT_CUSTODY")
    require(crosswalk.get("bvh_source_sha256")==EXPECTED["vmdsource"],"WRONG_BVH_SOURCE")
    require(crosswalk.get("vmd_sha256")==EXPECTED["vmd"],"VMD_BYTE_DIGEST")
    require(crosswalk.get("target_fps")==30 and crosswalk.get("source_frames")==3 and
            crosswalk.get("target_frame_pairs")==[[0,0],[2,1]] and
            crosswalk.get("source_frame_1")=="DROPPED_30FPS_RESAMPLE","UNDECLARED_BVH_TEMPORAL_LOSS")
    require(native.get("vmd_to_hier_usage")=="SPATIAL_CALIBRATION_ONLY_NO_TEMPORAL_HUMAN_RETARGET","FALSE_HUMAN_TEMPORAL_RETARGET")
    require(native.get("72f_hier_pose_source")=="SEPARATE_ORIGINAL_SYNTHETIC_FIXTURE_HIP_KNEE_ONLY","UNQUALIFIED_NATIVE_POSE_SOURCE")
    require(native.get("fps")==12 and native.get("views")=={"front":72,"oblique":72,"debug_front":72},"NATIVE_VIDEO_FRAME_BUDGET")
    rigs=native.get("parented_real_multiweight_rigs",{})
    require(set(rigs)=={"CobaltOriginal","MarigoldOriginal"},"TWO_ACTOR_INTEGRATED_RIG_ROSTER")
    for actor,rig in rigs.items():
        require(rig.get("connected_edges")==2 and rig.get("blended_knee_vertices")==2,"NO_REAL_PARENTED_MULTISKIN:"+actor)
        for metric in ("actual_evaluated_skin_motion_f0_f6_m","source_to_native_meter_gain"):
            v=rig.get(metric)
            require(isinstance(v,(int,float)) and math.isfinite(v),"NONFINITE_NATIVE_METRIC:"+metric)
        require(rig["actual_evaluated_skin_motion_f0_f6_m"]>.015 and
                abs(rig["source_to_native_meter_gain"]-1)<1e-5 and
                rig.get("rewind_error_m",99)<1e-6,"NATIVE_MOTION_OR_REWIND:"+actor)
    require(visual.get("schema")=="scp.r009.public-allframe-clean-visibility.v1" and
            visual.get("status")=="PASS_ORIGINAL_SYNTHETIC_RGB_VISIBILITY_ONLY" and
            visual.get("frame_count")==72,"FALSE_VISIBILITY_ACCEPTANCE")
    require(visual.get("trace_sha256")==EXPECTED["trace"],"FALSE_VISUAL_SOURCE_CUSTODY")
    require(set(visual.get("observed_clean_views",[]))=={"front","oblique"},"TWO_CAMERA_OR_ROLE_ALIAS")
    for key in ("front/CobaltOriginal","oblique/CobaltOriginal","front/MarigoldOriginal","oblique/MarigoldOriginal"):
        v=visual.get("roi_color_counts",{}).get(key)
        require(isinstance(v,dict) and v.get("frames_observed")==72 and v.get("min_roi_pixels",0)>10,
                "MISSING_ALL72_PIXEL_OBSERVER:"+key)
    decoded=visual.get("decoded_rgb_sha256",{})
    require(set(decoded)=={"front","oblique"} and decoded["front"]!=decoded["oblique"],"ALIASED_DECODED_CAMERA")
    require(foot.get("schema")=="scp.r009.public-debug-foot-video-observer.v1" and
            foot.get("status")=="PASS_AUTHORED_SYNTHETIC_DEBUG_MARKER_VISIBILITY_ONLY" and
            foot.get("frames")==72 and foot.get("inspected_source_foot_labels")==288,
            "AUTHOR_CONTACT_DEBUG_NOT_72F")
    require(foot.get("source_sha256")==EXPECTED["trace"],"MARKER_WRONG_TRACE")
    for actor in rigs:
        c=foot.get("per_actor_observation_counts",{}).get(actor,{})
        require(c.get("frames_any_visible")==72 and c.get("contact_visible",0)>=18 and
                c.get("swing_visible",0)>=12,"MARKER_PALETTE_VISIBILITY_INSUFFICIENT:"+actor)
    require(isinstance(negative,dict) and negative.get("rejected") is True and
            negative.get("kind")=="PHYSICALLY_REENCODED_H264_FRAME36" and
            negative.get("reason")=="VISUAL_OCCLUSION_OR_ACTOR_DROPOUT:oblique/MarigoldOriginal",
            "INDEPENDENT_REAL_H264_NEGATIVE_NOT_ADMITTED")
    require(set(media)=={"front","oblique","debug_front"},"MEDIA_VIEW_SET")
    for view,raw in media.items():
        require(isinstance(raw,(bytes,bytearray)) and len(raw)>1000 and
                raw[4:8]==b"ftyp","MISSING_OR_NOT_MP4:"+view)
    require(len({sha(raw) for raw in media.values()})==3,"ALIASED_ENCODED_VIDEOS")
    # Independent producer contracts spell the hold status differently:
    # original renderer private_r009, motion reviewers private_R009,
    # and debug-foot observer protected_R009. Do not synthesize an absent hold.
    # Explicitly require at least one and reject every conflicting extra field.
    for evidence in (native,visual,foot,crosswalk):
        declared=[evidence[k] for k in ("private_R009","private_r009","protected_R009") if k in evidence]
        require(bool(declared) and all(v=="HELD_NOT_ACCEPTED" for v in declared),
                "PROTECTED_R009_UNAUTHORIZED_PROMOTION")
    require(native.get("physical_biomechanics")=="UNKNOWN" and
            native.get("original_identity")=="NOT_ADMITTED" and
            visual.get("human_anatomy_ROM_JCS")=="UNKNOWN" and
            foot.get("human_JCS_ROM")=="UNKNOWN","UNAUTHORIZED_BIOPHYSICAL_CLAIM")
    require(negative.get("private_R009")=="HELD_NOT_ACCEPTED","NEGATIVE_BYPASS")
    return {
      "schema":SCHEMA,
      "status":"PASS_REPRODUCIBLE_ORIGINAL_SYNTHETIC_EVIDENCE_PROJECTION_ONLY",
      "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
      "immutable_donor_head_shas":DONORS,
      "media_sha256":{v:sha(b) for v,b in sorted(media.items())},
      "published_views":["front","oblique","debug_front"],
      "human":{"status":"SYNTHETIC_QUALIFICATION_ONLY","evidence":"72f 2 actor clean RGB, isolated 72f debug foot markers","human_ROM_contact":"UNKNOWN","protected_MVP":"HELD"},
      "automation":{"schema_version":1,"checks":["native_multiskin","bvh_vmd_source_signed_calibration_only","full72_clean_pixel","debug_foot","actual_encoded_H264_negative"],"status":"PASS_SOURCE_SAFE_ENGINEERING_ONLY"},
      "agent":{"read_only_actions":["capabilities","inspect_receipts","verify_source_safe"],"can_admit_protected_sources":False,"can_merge_release_deploy_cpe":False},
      "source_clock":{"bvh_frames":3,"bvh_fps":60,"vmd_frames":2,"vmd_fps":30,"dropped_bvh_frame":1,
                      "final_synthetic_video_frames":72,"video_fps":12,"temporal_human_retarget":"NOT_IMPLEMENTED"},
      "science":{"measured_ground_forces":"UNKNOWN","independent_JCS_ROM":"UNKNOWN","human_identity":"NOT_ADMITTED"},
      "private_R009":"HELD_NOT_ACCEPTED","merge":"HELD","release":"HELD","deployment":"HELD","CPE":"NOT_PROMOTED"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--capabilities",action="store_true")
    for k in ("native","visual","foot","crosswalk","negative","donors","front","oblique","debug_front","out"):
        p.add_argument("--"+k)
    a=p.parse_args()
    if a.capabilities:
        print(json.dumps({"schema":"scp.r009.native-evidence-capabilities.v1",
             "actions":["capabilities","verify_public_synthetic_only"],
             "owner_authorized_promotions":False,"private_R009":"HELD_NOT_ACCEPTED"},sort_keys=True))
        return
    try:
        for k in ("native","visual","foot","crosswalk","negative","donors","front","oblique","debug_front","out"):
            require(getattr(a,k),"MISSING_REQUIRED_EVIDENCE_ARG:"+k)
        r=check(read(a.native),read(a.visual),read(a.foot),read(a.crosswalk),
             {k:pathlib.Path(getattr(a,k)).read_bytes() for k in ("front","oblique","debug_front")},
             read(a.donors),read(a.negative))
        with pathlib.Path(a.out).open("x") as f:json.dump(r,f,indent=2,sort_keys=True);f.write("\n")
        print(json.dumps(r,sort_keys=True))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print("INTEGRATION_ADMISSION_REJECT:"+str(exc),file=sys.stderr)
        raise SystemExit(2)
if __name__=="__main__":main()
