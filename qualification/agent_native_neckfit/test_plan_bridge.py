import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from plan_bridge import proposal, validate, load_plan

def make_plan(p):
    out={"schema":"scp.actor_candidate_plan.v1","experiment_id":p["experiment_id"],
         "joint":"neck","axis":"Z","baseline_sha256":p["baseline_sha256"],
         "reference_sha256":p["reference_sha256"],"disposition":"VALID_PLAN_ONLY",
         "limits":"candidate-only bound","execution":False,"candidate_plans":[]}
    for i,angle in enumerate((-.6,0.,.6)):
        wire=f'{p["experiment_id"]}|{p["baseline_sha256"]}|{p["reference_sha256"]}|neck|Z|{i}|{angle:.17g}'
        out["candidate_plans"].append({"index":i,"angle_radians":angle,
            "candidate_id":hashlib.sha256(wire.encode()).hexdigest()})
    return out

class PlanBridge(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory()
        self.path=Path(self.work.name)
        self.model=self.path/"model.blend";self.model.write_bytes(b"original-public-synthetic-blend")
        self.ref=self.path/"source.glb";self.ref.write_bytes(b"original-public-synthetic-glb")
        self.p=proposal(self.model,self.ref)
        self.plan=make_plan(self.p)
    def tearDown(self):self.work.cleanup()
    def test_positive_and_stability(self):
        a=validate(self.model,self.ref,self.plan)
        b=validate(self.model,self.ref,self.plan)
        self.assertEqual(a,b)
        self.assertEqual(a["candidate_deltas_radians"],[-.6,0.,.6])
        self.assertFalse(a["model_promotion"])
        self.assertEqual(len(a["candidate_ids"]),3)
    def test_stale_source(self):
        self.model.write_bytes(b"tampered")
        with self.assertRaises(ValueError):validate(self.model,self.ref,self.plan)
    def test_stale_evidence(self):
        self.ref.write_bytes(b"tampered")
        with self.assertRaises(ValueError):validate(self.model,self.ref,self.plan)
    def test_adversarial(self):
        changes={
         "unauthorized_joint":lambda x:x.update(joint="carpus"),
         "execution":lambda x:x.update(execution=True),
         "range_extension":lambda x:x["candidate_plans"][2].update(angle_radians=1.4),
         "duplicate_id":lambda x:x["candidate_plans"][1].update(candidate_id=x["candidate_plans"][0]["candidate_id"]),
         "stale_id":lambda x:x["candidate_plans"][0].update(candidate_id="x"*64),
         "missing":lambda x:x.pop("reference_sha256"),
         "unexpected":lambda x:x.update(shell="rm -rf"),
         "index":lambda x:x["candidate_plans"][0].update(index=1),
         "extra_candidate":lambda x:x["candidate_plans"].append({"index":3,"angle_radians":.7,"candidate_id":"x"}),
        }
        for name,mut in changes.items():
            with self.subTest(name=name):
                x=copy.deepcopy(self.plan);mut(x)
                with self.assertRaises(ValueError):validate(self.model,self.ref,x)
    def test_duplicate_json_keys(self):
        path=self.path/"bad.json"
        path.write_text('{"schema":"a","schema":"b"}')
        with self.assertRaises(ValueError):load_plan(path)
    def test_trailing_json(self):
        path=self.path/"bad.json"
        path.write_text(json.dumps(self.plan)+" {}")
        with self.assertRaises(json.JSONDecodeError):load_plan(path)

if __name__=="__main__":unittest.main()
