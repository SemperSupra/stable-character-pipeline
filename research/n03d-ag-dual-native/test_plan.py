"""Hostile capped 2x2 native-actuator configuration / independent critic controls."""
import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from plan import actor_plan,corrections,independent_plan,capxy,first_window,MODES,BOUNDS,ACTORS,SIDES
from critic import assess

def actor(name):
    sides={}
    for side in SIDES:
        rows=[]
        for n in range(360):
            t=n/60
            rows.append({"index":n,"time_s":t,
                         "source_hip":[t*.5,.78,0.],
                         "source_ankle":[0.,.01,0.],
                         "source_toe":[0.,0.,.2],
                         "target_hip":[.5+t*.6,0.,.9],
                         "target_foot":[t*.3+.5,0.,.01],
                         "target_shoe_min_z":-.02})
        sides[side]=rows
    return {"name":name,"sides":sides}

def witness():
    actors=[]
    for name in ACTORS:
        a=actor(name);_,paths,starts=actor_plan(a)
        windows=[]
        for source_side in SIDES:
            start=starts[source_side]
            for bound in BOUNDS:
                for mode in MODES:
                    samples=[]
                    for n in range(start,start+6):
                        plan=corrections(a,paths,n,mode,bound)
                        xy=[a["sides"]["L"][n]["target_foot"][0],0]
                        obj={"bone_head_xy_m":xy,"material_xy_m":[0,0],"min_z_m":-.02}
                        cand={"bone_head_xy_m":xy,"material_xy_m":[0,0],"min_z_m":-.02}
                        samples.append({"source_index":n,"source_time_s":n/60,"plan":plan,
                                        "source":{s:copy.deepcopy(obj) for s in SIDES},
                                        "candidate":{s:copy.deepcopy(cand) for s in SIDES},
                                        "actual_target_foot_head_residual_xy_m":{s:0 for s in SIDES},
                                        "max_native_five_bone_pose_delta_rad":0})
                    windows.append({"actor":name,"source_selected_side":source_side,
                                    "first_source_sample":start,"mode":mode,"bound_m":bound,
                                    "source_contact_proven":False,"heel_toe_anatomy_verified":False,
                                    "real_native_both_legs_installed":True,"samples":samples})
        actors.append({"actor":name,"windows":windows})
    return {"schema":"scp.n03d-ag.actual-dual-leg-native-factorial.v1",
            "source_class":"ORIGINAL_FICTIONAL_CC0",
            "source_motion_changed":False,"corrected_blend_saved":False,
            "native_5bone_and_root_actuators_executed":True,
            "source_stance_proven":False,
            "anatomical_foot_correspondence_proven":False,
            "independent_visual_review_completed":False,
            "mvp_accepted":False,"actors":actors}

class AG(unittest.TestCase):
    def test_capped(self):
        self.assertAlmostEqual(math.hypot(*capxy([.12,.16],.08)),.08,9)
    def test_nonfinite_correction(self):
        with self.assertRaisesRegex(ValueError,"NONFINITE_CORRECTION"):capxy([math.inf,0],.08)
    def test_no_candidate_not_force(self):
        self.assertIsNone(first_window([180,182,190,191],size=6))
    def test_eligible_source_window(self):
        _,_,starts=actor_plan(actor(ACTORS[0]))
        self.assertEqual(starts,{"L":180,"R":180})
    def test_both_budgets(self):
        a=actor(ACTORS[0]);_,paths,_=actor_plan(a)
        for mode in MODES:
            for b in BOUNDS:
                plan=corrections(a,paths,190,mode,b)
                self.assertTrue(independent_plan(plan))
                self.assertLessEqual(math.hypot(*plan["root_delta_xy_m"]),b+1e-7)
    def test_no_root_for_original_or_leg_only(self):
        a=actor(ACTORS[0]);_,paths,_=actor_plan(a)
        for m in ("original","leg_only"):
            d=corrections(a,paths,200,m,.04)
            self.assertEqual(d["root_delta_xy_m"],[0,0])
    def test_no_leg_for_root_only(self):
        a=actor(ACTORS[0]);_,paths,_=actor_plan(a)
        d=corrections(a,paths,200,"root_only",.08)
        self.assertEqual(d["leg"]["L"]["delta_xy_m"],[0,0])
    def test_invalid_mode(self):
        a=actor(ACTORS[0]);_,paths,_=actor_plan(a)
        with self.assertRaisesRegex(ValueError,"MODE_OR_TIMEBASE"):corrections(a,paths,200,"bogus",.08)
    def test_forged_source_contact(self):
        a=actor(ACTORS[0]);_,paths,_=actor_plan(a)
        d=corrections(a,paths,200,"joint",.08)
        d["source_physical_plant_proven"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_CONTACT"):independent_plan(d)
    def test_critic_valid_but_physical_hold(self):
        x=assess(witness())
        self.assertEqual(x["status"],"HOLD")
        self.assertEqual(len(x["windows"]),32)
        self.assertTrue(any("SHOE_PENETRATION" in e for w in x["windows"] for e in w["physical_rejections"]))
        self.assertFalse(x["mvp_accepted"])
    def test_critic_wrong_side(self):
        d=witness();d["actors"][0]["windows"][0]["source_selected_side"]="Z"
        with self.assertRaisesRegex(ValueError,"WINDOW_KEY"):assess(d)
    def test_critic_forged_mvp(self):
        d=witness();d["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_OR_FALSE_PROMOTION"):assess(d)
    def test_critic_false_source_stance(self):
        d=witness();d["source_stance_proven"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_OR_FALSE_PROMOTION"):assess(d)
    def test_critic_missing_window(self):
        d=witness();d["actors"][1]["windows"].pop()
        with self.assertRaisesRegex(ValueError,"ACTOR_WINDOWS"):assess(d)
    def test_critic_nonfinite(self):
        d=witness();d["actors"][0]["windows"][0]["samples"][1]["candidate"]["L"]["min_z_m"]=math.nan
        with self.assertRaisesRegex(ValueError,"NONFINITE_OR_ABSURD"):assess(d)
    def test_critic_budget_exceeded(self):
        d=witness();d["actors"][0]["windows"][0]["samples"][1]["plan"]["root_delta_xy_m"]=[.4,0]
        with self.assertRaisesRegex(ValueError,"ROOT_BUDGET"):assess(d)

if __name__=="__main__":unittest.main()
