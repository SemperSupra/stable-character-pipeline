"""Analytic Lipschitz proof tests; exact recorded-source shape, rights, and hostile controls."""
import copy,hashlib,json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from temporal import minimum_lipschitz_majorant,evaluate,independent,N,HZ,LIMITS,SPEED_LIMITS,SIDES

def fixture():
    actors=[]
    for name in ("AsterOriginal","JuniperOriginal"):
        sides={}
        for s in SIDES:
            rows=[]
            for i in range(N):
                depth=-.085 if s==SIDES[0] and 35<=i<=40 else (-.012 if s==SIDES[1] else .02)
                rows.append({"t_s":round(i/HZ,9),"xy_m":[i*.005,0.],"z_m":depth})
            sides[s]={"samples":rows}
        actors.append({"actor":name,"native_bones":163,"sides":sides})
    trace={"schema":"scp.n03d-g.evaluated-foot-contact-observer.v1",
           "source_class":"ORIGINAL_FICTIONAL_CC0","frame_rate_hz":HZ,
           "sample_count_per_side":N,"heel_toe_anatomy_verified":False,
           "mvp_accepted":False,"source_scene_sha256":"f"*64,"actors":actors}
    checksum=hashlib.sha256((json.dumps(trace,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()).hexdigest()
    ac={"schema":"scp.n03d-ac.matched-source-to-bone-60hz.v1",
        "source_class":"ORIGINAL_FICTIONAL_CC0","source_scene_sha256":"f"*64,
        "source_shoe_trace_sha256":checksum,"source_motion_changed":False,
        "mvp_accepted":False}
    return trace,ac

class AI(unittest.TestCase):
    def test_exact_majorant_is_smallest_feasible(self):
        deficits=[0.]*N;deficits[40]=.08
        x=minimum_lipschitz_majorant(deficits,.25)
        self.assertAlmostEqual(x[40],.08)
        self.assertAlmostEqual(x[39],.08-.25/HZ)
        self.assertAlmostEqual(x[41],.08-.25/HZ)
        self.assertEqual(x[0],0.)
    def test_bound_slew(self):
        deficits=[.08 if i%3==0 else 0. for i in range(N)]
        for speed in SPEED_LIMITS:
            x=minimum_lipschitz_majorant(deficits,speed)
            self.assertTrue(all(x[i]>=deficits[i] for i in range(N)))
            self.assertTrue(all(abs(x[i]-x[i-1])<=speed/HZ+1e-10 for i in range(1,N)))
    def test_flat_input(self):
        self.assertEqual(minimum_lipschitz_majorant([0.]*N,.25),[0.]*N)
    def test_bad_speed(self):
        with self.assertRaisesRegex(ValueError,"SPEED_NOT_PREDECLARED"):
            minimum_lipschitz_majorant([0.]*N,5.)
    def test_negative_input(self):
        v=[0.]*N;v[5]=-.1
        with self.assertRaisesRegex(ValueError,"NEGATIVE_OR_MISSING_DEFICIT"):
            minimum_lipschitz_majorant(v,.25)
    def test_nonfinite_input(self):
        v=[0.]*N;v[5]=math.inf
        with self.assertRaisesRegex(ValueError,"INVALID_NONFINITE_NUMBER"):
            minimum_lipschitz_majorant(v,.25)
    def test_real_source_schema_original_fixture(self):
        t,a=fixture()
        r=evaluate(t,a)
        self.assertEqual(independent(r),"HOLD")
        self.assertEqual(len(r["actors"]),2)
        self.assertTrue(all(len(x["trials"])==6 for x in r["actors"]))
        x=r["actors"][0]["trials"]
        self.assertFalse(next(y for y in x if y["root_budget_m"]==.04)["full_plane_nonpenetration_feasible_with_budget"])
        self.assertTrue(next(y for y in x if y["root_budget_m"]==.12)["full_plane_nonpenetration_feasible_with_budget"])
    def test_intermediate_bilateral_above_reference_is_not_contact(self):
        r=evaluate(*fixture())
        x=r["actors"][0]["trials"]
        self.assertTrue(all(not z["physical_support_contact_verified"] for z in x))
        self.assertFalse(r["gait_accepted"])
    def test_wrong_trace_rights(self):
        t,a=fixture();t["source_class"]="PRIVATE_NAOMI"
        with self.assertRaisesRegex(ValueError,"SOURCE_TRACE_RIGHTS"):evaluate(t,a)
    def test_fake_source_hash(self):
        t,a=fixture();a["source_shoe_trace_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"SOURCE_AC_JOIN"):evaluate(t,a)
    def test_timebase_changed(self):
        t,a=fixture();t["actors"][0]["sides"][SIDES[0]]["samples"][3]["t_s"]+=.02
        a["source_shoe_trace_sha256"]=hashlib.sha256((json.dumps(t,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,"SOURCE_SHOE_TIMEBASE"):evaluate(t,a)
    def test_missing_shoe_side(self):
        t,a=fixture();del t["actors"][0]["sides"][SIDES[1]]
        a["source_shoe_trace_sha256"]=hashlib.sha256((json.dumps(t,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,"SHOE_ACTOR_OR_SIDE"):evaluate(t,a)
    def test_forged_release(self):
        r=evaluate(*fixture());r["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_PHYSICAL_ACCEPTANCE"):independent(r)
    def test_forged_native_actuation(self):
        r=evaluate(*fixture());r["native_motion_actuated"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_PHYSICAL_ACCEPTANCE"):independent(r)
    def test_budget_tamper(self):
        r=evaluate(*fixture());r["actors"][0]["trials"][0]["predicted_root_lift_m"][30]=.5
        with self.assertRaisesRegex(ValueError,"LIFT_BUDGET"):independent(r)
    def test_budget_pair_missing(self):
        r=evaluate(*fixture());r["actors"][0]["trials"].pop()
        with self.assertRaisesRegex(ValueError,"FACTORIAL_COUNT"):independent(r)

if __name__=="__main__":unittest.main()
