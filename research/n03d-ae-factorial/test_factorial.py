"""Adversarial real-source-compatible 60Hz root/leg factor tests."""
import copy,json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from factorial import evaluate,independent,candidate,source_eligible,MODES

def fixture():
    actors=[]
    for name in ("AsterOriginal","JuniperOriginal"):
        sides={}
        for side in ("L","R"):
            rows=[]
            for i in range(360):
                t=i/60
                rows.append({
                    "index":i,"time_s":t,
                    "source_hip":[.5*t,.75,0],
                    "source_ankle":[0,.02,0],
                    "source_toe":[0,0,.15],
                    "target_hip":[1+.6*t,0,.85],
                    "target_foot":[1+.4*t,0,.02],
                    "target_shoe_min_z":0
                })
            sides[side]=rows
        actors.append({"name":name,"sides":sides})
    return {"schema":"scp.n03d-ac.matched-source-to-bone-60hz.v1","source_class":"ORIGINAL_FICTIONAL_CC0",
            "source_motion_changed":False,"mvp_accepted":False,"actors":actors}

class Factorial(unittest.TestCase):
    def test_original_synthetic_matrix(self):
        x=evaluate(fixture());self.assertEqual(independent(x),"HOLD")
        self.assertEqual(len(x["actors"]),2)
        for a in x["actors"]:
            for s in a["sides"]:
                self.assertGreater(s["heldout_candidate_intervals"],0)
                self.assertEqual(set(s["ablation"]),set(MODES))
                self.assertGreater(s["ablation"]["original"]["p50_mps"],.3)
                self.assertLess(s["ablation"]["joint"]["p50_mps"],1e-5)
    def test_train_holdout(self):
        x=evaluate(fixture());self.assertEqual(x["train_samples"],[0,179]);self.assertEqual(x["heldout_samples"],[180,359])
    def test_stance_source_selection_is_independent_of_target(self):
        a=fixture()["actors"][0]["sides"]["L"]
        b=copy.deepcopy(a)
        for row in b:row["target_foot"][0]+=row["time_s"]*20
        self.assertEqual(source_eligible(a),source_eligible(b))
    def test_wrong_side(self):
        d=fixture();del d["actors"][1]["sides"]["R"]
        with self.assertRaises(ValueError):evaluate(d)
    def test_bad_timebase(self):
        d=fixture();d["actors"][0]["sides"]["L"][64]["time_s"]+=.01
        with self.assertRaises(ValueError):evaluate(d)
    def test_nonfinite_root(self):
        d=fixture();d["actors"][1]["sides"]["R"][0]["source_hip"][0]=math.nan
        with self.assertRaises(ValueError):evaluate(d)
    def test_degenerate_root_fit(self):
        d=fixture()
        for a in d["actors"]:
            for side in ("L","R"):
                for row in a["sides"][side]:row["source_hip"]=[0,.75,0]
        with self.assertRaisesRegex(ValueError,"DEGENERATE_SOURCE_PATH"):evaluate(d)
    def test_forged_native(self):
        s=evaluate(fixture());s["native_actuation_performed"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_ABLATION_PROMOTION"):independent(s)
    def test_forged_release(self):
        s=evaluate(fixture());s["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_ABLATION_PROMOTION"):independent(s)
    def test_missing_mode(self):
        s=evaluate(fixture());del s["actors"][0]["sides"][0]["ablation"]["joint"]
        with self.assertRaisesRegex(ValueError,"INCOMPLETE_FACTORIAL"):independent(s)
    def test_tampered_metric(self):
        s=evaluate(fixture());s["actors"][0]["sides"][0]["ablation"]["joint"]["p50_mps"]=math.nan
        with self.assertRaisesRegex(ValueError,"NONFINITE_METRICS"):independent(s)
    def test_fake_contact(self):
        s=evaluate(fixture());s["actors"][0]["sides"][0]["heldout_contact_truth_known"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_NATIVE_OR_CONTACT_PROOF"):independent(s)

if __name__=="__main__":unittest.main()
