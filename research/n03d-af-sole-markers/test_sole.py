"""Adversarial original geometry and physical nonpromotion fixtures."""
import copy, math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from sole import project,snapshot,metric,assess
def pts():
    out=[]
    for side in (-1,1):
        for i in range(80):
            for j in range(10):
                out.append([side*.2+.001*j,-.2+.006*i,.001*j])
    return out
def selected():
    a=pts()
    return a,project(a,list(range(800)),(0,.3))
def doc():
    xyz,co=selected()
    windows=[]
    for actor in ("AsterOriginal","JuniperOriginal"):
        for side in ("L","R"):
            for start in (24,48):
                windows.append(dict(actor=actor,side=side,start_24hz=start,cohort=copy.deepcopy(co),
                    heel_samples=[dict(t_s=(start+j)/24,xy_m=[0,0],min_z_m=0) for j in range(12)],
                    toe_samples=[dict(t_s=(start+j)/24,xy_m=[.3,0],min_z_m=0) for j in range(12)]))
    return dict(schema="scp.n03d-af.real-shoe-plantar-proxy.v1",source_class="ORIGINAL_FICTIONAL_CC0",
                source_scene_unchanged=True,actual_anatomy_accepted=False,mvp_accepted=False,windows=windows)
class C(unittest.TestCase):
    def test_cohort(self):
        xyz,x=selected();self.assertGreater(x["proxy_heel_to_toe_separation_m"],.025)
        self.assertFalse(set(x["heel_proxy_vertex_ids"])&set(x["toe_proxy_vertex_ids"]))
    def test_independent_ids(self):
        xyz,x=selected()
        q=snapshot(xyz,x["heel_proxy_vertex_ids"])
        self.assertTrue(math.isfinite(q["min_z_m"]))
    def test_short_axis(self):
        a=pts()
        with self.assertRaisesRegex(ValueError,"FOOT_AXIS_TOO_SHORT"):project(a,list(range(800)),(0,.001))
    def test_duplicate_ids(self):
        a=pts()
        with self.assertRaisesRegex(ValueError,"VERTEX_ID_DUPLICATE_OR_RANGE"):project(a,[0]*100,(0,1))
    def test_nans(self):
        a=pts();a[0][1]=math.nan
        with self.assertRaisesRegex(ValueError,"INVALID_WORLD_VERTEX"):project(a,list(range(800)),(0,1))
    def test_false_heel_toe_promotion(self):
        d=doc();d["windows"][0]["cohort"]["actual_anatomical_heel_ball_toe_verified"]=True
        with self.assertRaisesRegex(ValueError,"COHORT_UNQUALIFIED"):assess(d)
    def test_forced_anatomical_pass(self):
        d=doc();d["actual_anatomy_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_FALSE_ACCEPTANCE"):assess(d)
    def test_protected_source(self):
        d=doc();d["source_class"]="NAOMI_PRIVATE"
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_FALSE_ACCEPTANCE"):assess(d)
    def test_fake_mvp(self):
        d=doc();d["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_FALSE_ACCEPTANCE"):assess(d)
    def test_missing_window(self):
        d=doc();d["windows"].pop()
        with self.assertRaisesRegex(ValueError,"WINDOW_FACTORIAL_COUNT"):assess(d)
    def test_duplicate_window(self):
        d=doc();d["windows"][1]=copy.deepcopy(d["windows"][0])
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OR_INVALID_WINDOW"):assess(d)
    def test_sliding_contact_even_though_near_floor(self):
        rows=[dict(t_s=i/24,xy_m=[i*.04,0],min_z_m=0) for i in range(12)]
        m=metric(rows)
        self.assertEqual(m["near_ground_adjacent_pairs"],11)
        self.assertGreater(m["p50_near_mps"],.08)
    def test_nonfinite_time(self):
        d=doc();d["windows"][0]["heel_samples"][2]["t_s"]=math.inf
        with self.assertRaisesRegex(ValueError,"SAMPLE_FORMAT"):assess(d)
    def test_valid_is_still_held(self):
        a=assess(doc());self.assertEqual(a["status"],"HOLD")
        self.assertEqual(len(a["windows"]),8)
        self.assertFalse(a["actual_contact_proven"])
if __name__=="__main__":unittest.main()
