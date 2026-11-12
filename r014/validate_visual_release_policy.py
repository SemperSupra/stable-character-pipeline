"""DLE executable visual/kinematic release policy; explicit negative controls.

A research evidence-capture success is never equivalent to photographic realism,
anatomical sex, FACS facial animation, natural gait or product readiness.
"""
import argparse,json,sys,unittest
from pathlib import Path
REQUIRED={
  "source":"model_family asset_revision asset_sha256 license_provenance source_gender_macro rigged_evaluated_mesh_id effective_render_vertices render_lod_evidence uv_material_provenance",
  "anatomy":"region_coverage_receipt external_reproductive_anatomy_review complete_hand_foot_facial_review",
  "deformation":"head_neck_shoulder_hip_hand_foot_extreme_pose foldover_test volume_contact_evidence native_export_parity",
  "motion":"root_translation ground_contact_events foot_slip_measurement start_stop_turn finger_independent_articulation thumb_opposition jaw_gaze lip_brow_cheek_controls viseme_coverage temporal_consistency",
  "surface":"skin_sss_microdetail hair_groom eye_cornea_iris lips_teeth_tongue material_licensing_and_uv_seams",
  "qa":"h264_or_approved_codec frame_consistency foreground_and_crop_metrics independent_visual_anatomy_review independent_motion_review model_source_comparison failclosed_receipts",
}
REQUIRED={k:set(v.split()) for k,v in REQUIRED.items()}
def check_policy(policy):
    assert policy["release_state"]=="HOLD"
    assert policy["schema_version"]=="r014.visual.release.v1"
    for k,expected in REQUIRED.items():
        assert expected<=set(policy["evidence_requirements"][k]),(k,expected-set(policy["evidence_requirements"][k]))
    stages=policy["tiers"]
    assert stages["intermediate_visual"]["min_width"]>=1920
    assert stages["cinematic_candidate"]["min_width"]>=3840
    assert stages["cinematic_candidate"]["min_height"]>=2160
    assert len(policy["non_negotiable_checks"])>=8
    return True
def judge(policy,evidence):
    violations=[]
    for k,fields in REQUIRED.items():
        fields_state=evidence.get(k,{})
        for key in sorted(fields):
            if fields_state.get(key)!="accepted":
                violations.append(k+"."+key)
    if evidence.get("controlled_female_macro")!=0.:violations.append("controlled_female_macro")
    if evidence.get("controlled_male_macro")!=1.:violations.append("controlled_male_macro")
    if not evidence.get("human_approver"):violations.append("human_approver")
    video=evidence.get("video",{})
    if video.get("width",0)<3840 or video.get("height",0)<2160:
        violations.append("cinematic_resolution")
    return {"state":"READY_FOR_OWNER_RELEASE_DECISION" if not violations else "HOLD",
            "rejected_gate_count":len(violations),"reasons":violations}
class Controls(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(Path(__file__).with_name("visual_release_policy.json").read_text())
        check_policy(self.p)
        self.complete={k:{f:"accepted" for f in req} for k,req in REQUIRED.items()}
        self.complete.update({"controlled_female_macro":0.0,"controlled_male_macro":1.0,
                              "human_approver":"independent documented reviewer",
                              "video":{"width":3840,"height":2160}})
    def test_full_evidence_is_only_ready_for_owner_decision(self):
        self.assertEqual(judge(self.p,self.complete)["state"],"READY_FOR_OWNER_RELEASE_DECISION")
    def test_no_highres_proof_stays_held(self):
        e=json.loads(json.dumps(self.complete));e["source"]["rigged_evaluated_mesh_id"]="missing"
        self.assertIn("source.rigged_evaluated_mesh_id",judge(self.p,e)["reasons"])
    def test_wrong_body_preset_stays_held(self):
        e=json.loads(json.dumps(self.complete));e["controlled_female_macro"]=1.0
        self.assertIn("controlled_female_macro",judge(self.p,e)["reasons"])
    def test_lip_cheek_brow_not_jaw_only(self):
        e=json.loads(json.dumps(self.complete));e["motion"]["lip_brow_cheek_controls"]="not_authored"
        self.assertIn("motion.lip_brow_cheek_controls",judge(self.p,e)["reasons"])
    def test_handless_and_footless_video_held(self):
        e=json.loads(json.dumps(self.complete));e["motion"]["thumb_opposition"]="missing"
        e["motion"]["ground_contact_events"]="missing"
        self.assertEqual(judge(self.p,e)["state"],"HOLD")
    def test_pixel_count_not_enough(self):
        e=json.loads(json.dumps(self.complete));e["video"]["width"]=448
        self.assertIn("cinematic_resolution",judge(self.p,e)["reasons"])
if __name__=="__main__":
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]],verbosity=2)
    else:
        ap=argparse.ArgumentParser()
        ap.add_argument("--policy",type=Path,required=True)
        ap.add_argument("--evidence",type=Path)
        ap.add_argument("--out",type=Path,required=True)
        a=ap.parse_args()
        p=json.loads(a.policy.read_text())
        check_policy(p)
        e=json.loads(a.evidence.read_text()) if a.evidence else {}
        result=judge(p,e)
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print("R014_RELEASE_POLICY",json.dumps(result,sort_keys=True))
        if result["state"]!="HOLD":
            raise SystemExit("This unqualified research workcell must NOT auto-release")
