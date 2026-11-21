"""AK strict native source, 24/60Hz and forged-acceptance falsifiers."""
import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import ACTORS,SIDES,CHOSEN,N24,N60,assess,lerp
def fixture():
    actors=[]
    for name in ACTORS:
        trials=[]
        for cap,speed in CHOSEN:
            byclock={}
            for label,rate,count in (("24hz",24,N24),("60hz",60,N60)):
                rows=[]
                for i in range(count):
                    lift=.04
                    shoes={s:{"source_z_m":-.02,"candidate_z_m":.02,
                              "source_xy_m":[0.,0.],"candidate_xy_m":[0.,0.]} for s in SIDES}
                    rows.append({"index":i,"time_s":i/rate,"root_world_lift_m":lift,"shoes":shoes})
                byclock[label]=rows
            trials.append({"budget_m":cap,"slew_mps":speed,
                           "shoe_partitions_are_anatomical":False,
                           "root_only_no_leg_ik":True,
                           "source_ground_is_scene_Z0_only":True,"samples":byclock})
        actors.append({"actor":name,"rig_bones":163,"trials":trials})
    return {"schema":"scp.n03d-ak.native-lipschitz-root-z.v1",
            "source_class":"ORIGINAL_FICTIONAL_CC0","source_scene_unchanged":True,
            "actual_native_root_world_actuated":True,"root_curve_saved":False,
            "independent_floor_calibration_done":False,"anatomical_contact_verified":False,
            "source_force_proven":False,"independent_visual_review":False,
            "mvp_accepted":False,"actors":actors}
class AK(unittest.TestCase):
    def test_synthetic_replay_is_not_contact(self):
        r=assess(fixture());self.assertEqual(r["status"],"HOLD")
        self.assertEqual(len(r["trials"]),8)
        self.assertFalse(r["physical_contact_accepted"])
    def test_lerp_bounds(self):
        x=[i/1000 for i in range(N24)]
        self.assertAlmostEqual(lerp(x,1/60),.0004,8)
        self.assertAlmostEqual(lerp(x,142/24),.142,8)
    def test_lerp_just_past_clip(self):
        with self.assertRaisesRegex(ValueError,"OUT_OF_SCENE"):lerp([0.]*N24,5.95)
    def test_wrong_clock(self):
        d=fixture();d["actors"][0]["trials"][0]["samples"]["60hz"][7]["time_s"]+=.01
        with self.assertRaisesRegex(ValueError,"TIMEBASE_OR_SIDE"):assess(d)
    def test_bad_budget(self):
        d=fixture();d["actors"][0]["trials"][0]["samples"]["24hz"][0]["root_world_lift_m"]=.13
        with self.assertRaisesRegex(ValueError,"ROOT_LIFT_BUDGET"):assess(d)
    def test_false_vertical_evidence(self):
        d=fixture();d["actors"][0]["trials"][0]["samples"]["24hz"][0]["shoes"][SIDES[0]]["candidate_z_m"]=.01
        with self.assertRaisesRegex(ValueError,"NATIVE_RIGID_Z_DRIFT"):assess(d)
    def test_horizontal_leakage(self):
        d=fixture();d["actors"][1]["trials"][1]["samples"]["60hz"][1]["shoes"][SIDES[1]]["candidate_xy_m"][0]=.05
        with self.assertRaisesRegex(ValueError,"NATIVE_HORIZONTAL_SOURCE_LEAKAGE"):assess(d)
    def test_nonfinite_mesh(self):
        d=fixture();d["actors"][0]["trials"][2]["samples"]["60hz"][1]["shoes"][SIDES[0]]["source_z_m"]=math.nan
        with self.assertRaisesRegex(ValueError,"NONFINITE"):assess(d)
    def test_missing_shoe_side(self):
        d=fixture();del d["actors"][0]["trials"][0]["samples"]["24hz"][0]["shoes"][SIDES[0]]
        with self.assertRaisesRegex(ValueError,"TIMEBASE_OR_SIDE"):assess(d)
    def test_forged_ground(self):
        d=fixture();d["independent_floor_calibration_done"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_RIGHTS_OR_MVP_ACCEPTANCE"):assess(d)
    def test_forged_source_force(self):
        d=fixture();d["source_force_proven"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_RIGHTS_OR_MVP_ACCEPTANCE"):assess(d)
    def test_forged_anatomical(self):
        d=fixture();d["anatomical_contact_verified"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_RIGHTS_OR_MVP_ACCEPTANCE"):assess(d)
    def test_forged_movie(self):
        d=fixture();d["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_RIGHTS_OR_MVP_ACCEPTANCE"):assess(d)
    def test_unsaved_original(self):
        d=fixture();d["root_curve_saved"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_RIGHTS_OR_MVP_ACCEPTANCE"):assess(d)
    def test_spoofed_slew(self):
        d=fixture();d["actors"][0]["trials"][0]["samples"]["24hz"][2]["root_world_lift_m"]=.08
        with self.assertRaisesRegex(ValueError,"ROOT_SLEW_LIMIT"):assess(d)
if __name__=="__main__":unittest.main()
