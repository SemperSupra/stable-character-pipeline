#!/usr/bin/env python3
"""Self-authored contract fixtures: tests are NOT observational CI acceptance."""
import copy,importlib.util,unittest,pathlib
path=pathlib.Path(__file__).with_name("verify_evidence.py")
spec=importlib.util.spec_from_file_location("scp_r009_evidence",path)
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def fixtures():
    donor=dict(v.DONORS)
    native={
        "schema":"scp.r009.original-synthetic-integrated-native-park.v1",
        "status":"PASS_COMPOSED_ORIGINAL_SYNTHETIC_SOURCE_VMD_CALIBRATION_HIER_SKIN_AND_TWO_CAMERA",
        "original_source_sha256":v.EXPECTED["trace"],
        "hier_source_sha256":v.EXPECTED["hier"],
        "vmd_source_sha256":v.EXPECTED["vmd"],
        "source_fk_sha256":"e"*64,
        "vmd_to_hier_usage":"SPATIAL_CALIBRATION_ONLY_NO_TEMPORAL_HUMAN_RETARGET",
        "72f_hier_pose_source":"SEPARATE_ORIGINAL_SYNTHETIC_FIXTURE_HIP_KNEE_ONLY",
        "fps":12,"views":{"front":72,"oblique":72,"debug_front":72},
        "parented_real_multiweight_rigs":{
            a:{"connected_edges":2,"blended_knee_vertices":2,
               "actual_evaluated_skin_motion_f0_f6_m":.35,
               "source_to_native_meter_gain":1.0,
               "rewind_error_m":0.0}
            for a in ("CobaltOriginal","MarigoldOriginal")},
        "physical_biomechanics":"UNKNOWN",
        "original_identity":"NOT_ADMITTED",
        "private_R009":"HELD_NOT_ACCEPTED"
    }
    visual={
        "schema":"scp.r009.public-allframe-clean-visibility.v1",
        "status":"PASS_ORIGINAL_SYNTHETIC_RGB_VISIBILITY_ONLY",
        "trace_sha256":v.EXPECTED["trace"],"frame_count":72,
        "observed_clean_views":["front","oblique"],
        "roi_color_counts":{
           view+"/"+actor:{"frames_observed":72,"min_roi_pixels":40}
           for view in ("front","oblique")
           for actor in ("CobaltOriginal","MarigoldOriginal")},
        "decoded_rgb_sha256":{"front":"a"*64,"oblique":"b"*64},
        "human_anatomy_ROM_JCS":"UNKNOWN",
        "private_R009":"HELD_NOT_ACCEPTED"
    }
    foot={
        "schema":"scp.r009.public-debug-foot-video-observer.v1",
        "status":"PASS_AUTHORED_SYNTHETIC_DEBUG_MARKER_VISIBILITY_ONLY",
        "source_sha256":v.EXPECTED["trace"],
        "frames":72,"inspected_source_foot_labels":288,
        "per_actor_observation_counts":{
           a:{"frames_any_visible":72,"contact_visible":90,"swing_visible":49}
           for a in ("CobaltOriginal","MarigoldOriginal")},
        "human_JCS_ROM":"UNKNOWN","private_R009":"HELD_NOT_ACCEPTED"
    }
    cross={
        "fk_receipt_sha256":"e"*64,
        "bvh_source_sha256":v.EXPECTED["vmdsource"],
        "vmd_sha256":v.EXPECTED["vmd"],
        "target_fps":30,"source_frames":3,
        "target_frame_pairs":[[0,0],[2,1]],
        "source_frame_1":"DROPPED_30FPS_RESAMPLE",
        "private_R009":"HELD_NOT_ACCEPTED"
    }
    clips={key:b"\x00\x00\x00\x18ftypisom"+(key.encode()*2000)
           for key in ("front","oblique","debug_front")}
    neg={"kind":"PHYSICALLY_REENCODED_H264_FRAME36",
         "rejected":True,
         "reason":"VISUAL_OCCLUSION_OR_ACTOR_DROPOUT:oblique/MarigoldOriginal",
         "private_R009":"HELD_NOT_ACCEPTED"}
    return [native,visual,foot,cross,clips,donor,neg]

class OriginalOnlyContract(unittest.TestCase):
    def test_fixture_baseline_is_only_source_synthetic(self):
        out=v.check(*fixtures())
        self.assertEqual(out["private_R009"],"HELD_NOT_ACCEPTED")
        self.assertEqual(out["agent"]["can_merge_release_deploy_cpe"],False)
        self.assertEqual(out["science"]["human_identity"],"NOT_ADMITTED")
        self.assertEqual(out["status"],"PASS_REPRODUCIBLE_ORIGINAL_SYNTHETIC_EVIDENCE_PROJECTION_ONLY")
    def test_mutant_separately_fails_specific_cause(self):
        cases=[
          ("forged_donor",5,"vmd_native","0"*40,"MUTABLE_OR_UNQUALIFIED_DONOR_HEAD"),
          ("human_promotion",0,"private_R009","ACCEPTED","PROTECTED_R009_UNAUTHORIZED_PROMOTION"),
          ("skipped_frame",0,"views",{"front":71,"oblique":72,"debug_front":72},"NATIVE_VIDEO_FRAME_BUDGET"),
          ("missing_rig",0,"parented_real_multiweight_rigs",{},"TWO_ACTOR_INTEGRATED_RIG_ROSTER"),
          ("frozen_skin",0,"parented_real_multiweight_rigs","FROZEN","NATIVE_MOTION_OR_REWIND"),
          ("missing_visual",1,"observed_clean_views",["front"],"TWO_CAMERA_OR_ROLE_ALIAS"),
          ("false_human",1,"human_anatomy_ROM_JCS","PASS","UNAUTHORIZED_BIOPHYSICAL_CLAIM"),
          ("clock_loss",3,"source_frame_1","DROPPED_IMPLICIT","UNDECLARED_BVH_TEMPORAL_LOSS"),
          ("vmd_source_hash",3,"vmd_sha256","a"*64,"VMD_BYTE_DIGEST"),
          ("no_real_negative",6,"rejected",False,"INDEPENDENT_REAL_H264_NEGATIVE_NOT_ADMITTED"),
          ("alias_encoded",4,"oblique","ALIAS","ALIASED_ENCODED_VIDEOS"),
          ("alias_decoded",1,"decoded_rgb_sha256","ALIAS","ALIASED_DECODED_CAMERA"),
          ("false_retarget",0,"vmd_to_hier_usage","FULL_HUMAN_RETARGET","FALSE_HUMAN_TEMPORAL_RETARGET"),
        ]
        for name,index,key,val,reason in cases:
            with self.subTest(name=name):
                a=copy.deepcopy(fixtures())
                if val=="FROZEN":
                    a[0]["parented_real_multiweight_rigs"]["CobaltOriginal"]["actual_evaluated_skin_motion_f0_f6_m"]=0
                elif val=="ALIAS":
                    a[4]["oblique"]=a[4]["front"]
                elif index==1 and key=="decoded_rgb_sha256":
                    a[1]["decoded_rgb_sha256"]["oblique"]=a[1]["decoded_rgb_sha256"]["front"]
                else:
                    a[index][key]=val
                with self.assertRaises(v.Reject) as caught:
                    v.check(*a)
                self.assertEqual(str(caught.exception),reason)
if __name__=="__main__":unittest.main()
