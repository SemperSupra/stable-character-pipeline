"""AH finite, temporal, zero-motion source null, safety, rights and budgets."""
import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from vertical import proposal,check_plan,temporal_metrics,ACTORS,SIDES,MODES,BOUNDS
from policy import assess

def fixture():
    actors=[]
    for name in ACTORS:
        windows=[]
        for side in SIDES:
            start=180 if side=="L" else 221
            for budget in BOUNDS:
                for mode in MODES:
                    rows=[]
                    for j in range(6):
                        n=start+j
                        before={"L":-.085,"R":-.013}
                        plan=proposal(before,budget,mode)
                        source={s:{"bone_head_xy_m":[0.,0.],"material_xy_m":[0.,0.],
                                   "min_z_m":before[s]} for s in SIDES}
                        target={s:{"bone_head_xy_m":[0.,0.],"material_xy_m":[0.,0.],
                                   "min_z_m":before[s]+plan["root_z_m"]+plan["leg_z_m"][s]} for s in SIDES}
                        foot_before={s:.1 for s in SIDES}
                        foot_after={s:.1+plan["root_z_m"]+plan["leg_z_m"][s] for s in SIDES}
                        rows.append({
                            "source_index":n,"source_time_s":n/60,"plan":plan,
                            "source":source,"candidate":target,
                            "source_foot_bone_head_z_m":foot_before,
                            "candidate_foot_bone_head_z_m":foot_after,
                            "actual_target_bone_vertical_residual_m":{s:0. for s in SIDES},
                            "max_fivebone_pose_rotation_rad":0.
                        })
                    windows.append({"actor":name,"source_selected_side":side,
                                    "first_source_sample":start,"mode":mode,"bound_m":budget,
                                    "reference_ground_z_m":0.0,
                                    "physical_stance_proven":False,
                                    "actual_anatomical_support_proven":False,
                                    "temporal_source_plan":temporal_metrics(rows),
                                    "samples":rows})
        actors.append({"actor":name,"windows":windows})
    return {"schema":"scp.n03d-ah.vertical-shoe-actual-native.v1",
            "source_class":"ORIGINAL_FICTIONAL_CC0","scene_source_unchanged":True,
            "corrected_animation_saved":False,"true_native_dual_leg_ik_executed":True,
            "physical_stance_proven":False,"floor_reference_calibrated":False,
            "anatomical_heel_ball_toe_verified":False,"independent_visual_review":False,
            "mvp_accepted":False,"actors":actors}

class AH(unittest.TestCase):
    def test_original_null(self):
        p=proposal({"L":-.08,"R":-.02},.04,"original")
        self.assertEqual(p["root_z_m"],0.)
        self.assertEqual(p["leg_z_m"],{"L":0.,"R":0.})
    def test_root_only_lift_cap(self):
        p=proposal({"L":-.085,"R":-.02},.04,"root_z")
        self.assertEqual(p["root_z_m"],.04)
        self.assertGreater(p["predicted_residual_penetration_m"]["L"],.04)
    def test_dual_leg_independent(self):
        p=proposal({"L":-.07,"R":0.02},.08,"legs_z")
        self.assertEqual(p["leg_z_m"]["R"],0.)
        self.assertEqual(p["leg_z_m"]["L"],.07)
    def test_joint_z_bounded(self):
        p=proposal({"L":-.085,"R":-.013},.04,"joint_z")
        self.assertAlmostEqual(p["root_z_m"],.04)
        self.assertAlmostEqual(p["leg_z_m"]["L"],.04)
        self.assertEqual(p["leg_z_m"]["R"],0.)
        self.assertTrue(check_plan(p))
    def test_bad_number(self):
        with self.assertRaisesRegex(ValueError,"NONFINITE_MEASUREMENT"):
            proposal({"L":math.nan,"R":0.},.08,"joint_z")
    def test_missing_side(self):
        with self.assertRaisesRegex(ValueError,"BILATERAL_SOURCE_REQUIRED"):
            proposal({"L":-.08},.08,"joint_z")
    def test_invalid_budget(self):
        with self.assertRaisesRegex(ValueError,"MODE_OR_BUDGET"):
            proposal({"L":-.08,"R":-.04},.12,"joint_z")
    def test_tampered_root_budget(self):
        p=proposal({"L":-.08,"R":-.04},.04,"joint_z");p["root_z_m"]=.09
        with self.assertRaisesRegex(ValueError,"ROOT_BUDGET"):check_plan(p)
    def test_tampered_leg_budget(self):
        p=proposal({"L":-.08,"R":-.04},.04,"joint_z");p["leg_z_m"]["L"]=.09
        with self.assertRaisesRegex(ValueError,"LEG_BUDGET"):check_plan(p)
    def test_forged_contact(self):
        p=proposal({"L":-.08,"R":-.04},.04,"joint_z");p["predicted_source_contact"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_CONTACT"):check_plan(p)
    def test_temporal_change_detected(self):
        rows=[{"source_index":i+180,"plan":{"root_z_m":.04 if i%2 else 0.}} for i in range(6)]
        self.assertGreater(temporal_metrics(rows)["max_root_acceleration_mps2"],0.)
    def test_synthetic_report_is_hold(self):
        v=assess(fixture());self.assertEqual(v["status"],"HOLD")
        self.assertEqual(len(v["windows"]),32)
        self.assertFalse(v["physical_gait_accepted"])
    def test_forged_mvp(self):
        x=fixture();x["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"PROVENANCE_OR_FORGED_PHYSICAL_ADMISSION"):assess(x)
    def test_bad_rights(self):
        x=fixture();x["source_class"]="PRIVATE_NAOMI"
        with self.assertRaisesRegex(ValueError,"PROVENANCE_OR_FORGED_PHYSICAL_ADMISSION"):assess(x)
    def test_tampered_timebase(self):
        x=fixture();x["actors"][0]["windows"][0]["samples"][2]["source_time_s"]+=.1
        with self.assertRaisesRegex(ValueError,"TIMEBASE"):assess(x)
    def test_forged_kinematic_witness(self):
        x=fixture();x["actors"][0]["windows"][0]["samples"][2]["candidate_foot_bone_head_z_m"]["L"]+=.1
        with self.assertRaisesRegex(ValueError,"VERTICAL_TARGET_RESIDUAL_WRONG"):assess(x)
    def test_worst_penetration_not_accepted(self):
        x=assess(fixture())
        self.assertTrue(any("L_PENETRATION_GT_10MM" in z["rejections"] for z in x["windows"]))
if __name__=="__main__":unittest.main()
