"""AJ original source-to-shoe Y/Z strict common clock and mapping controls."""
import copy,hashlib,json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from calibrate import evaluate,independent,SHOES

def fixture():
    actors=[];sources=[]
    for actor in ("AsterOriginal","JuniperOriginal"):
        sides={}
        for part,zshift in zip(SHOES,(-.04,.04)):
            sides[part]={"samples":[{"t_s":round(j/24,9),"z_m":zshift+.02*math.sin(j/18),
                                     "xy_m":[0.,0.]} for j in range(143)]}
        actors.append({"actor":actor,"native_bones":163,"sides":sides})
        source_sides={}
        for side in ("L","R"):
            source_sides[side]=[{"index":n,"time_s":n/60,
                 "source_toe":[0.,.02+(.01 if n>180 else 0),0.],
                 "source_ankle":[0.,.03+(.01 if n>180 else 0),0.]} for n in range(360)]
        sources.append({"name":actor,"sides":source_sides})
    tr={"schema":"scp.n03d-g.evaluated-foot-contact-observer.v1",
        "source_class":"ORIGINAL_FICTIONAL_CC0","frame_rate_hz":24,
        "sample_count_per_side":143,"heel_toe_anatomy_verified":False,
        "mvp_accepted":False,"source_scene_sha256":"a"*64,"actors":actors}
    ac={"schema":"scp.n03d-ac.matched-source-to-bone-60hz.v1",
        "source_class":"ORIGINAL_FICTIONAL_CC0","source_scene_sha256":"a"*64,
        "source_motion_changed":False,"mvp_accepted":False,"actors":sources}
    sign(tr,ac)
    return tr,ac
def sign(trace,ac):
    ac["source_shoe_trace_sha256"]=hashlib.sha256((json.dumps(trace,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()).hexdigest()

class Controls(unittest.TestCase):
    def test_original_fictional_is_hold(self):
        d=evaluate(*fixture())
        self.assertEqual(independent(d),"HOLD")
        self.assertEqual(len(d["actors"]),2)
    def test_exact_12hz_alignment(self):
        d=evaluate(*fixture())
        self.assertEqual(d["actors"][0]["clock"],"EXACT_COMMON_12HZ_72_POINTS")
    def test_both_side_assignments(self):
        d=evaluate(*fixture())
        self.assertEqual(len(d["actors"][0]["comparisons"]),2)
    def test_train_heldout(self):
        d=evaluate(*fixture());self.assertEqual(d["actors"][0]["train_sample_indices"],[0,35])
        for c in d["actors"][0]["comparisons"]:
            self.assertEqual(c["sides"]["L"]["train_fit"]["fit_source_samples"],36)
    def test_rights(self):
        t,a=fixture();t["source_class"]="PROTECTED"
        with self.assertRaisesRegex(ValueError,"SHOE_TRACE_AUTHORITY"):evaluate(t,a)
    def test_source_hash_mismatch(self):
        t,a=fixture();a["source_shoe_trace_sha256"]="b"*64
        with self.assertRaisesRegex(ValueError,"JOIN_OR_SOURCE_RIGHTS"):evaluate(t,a)
    def test_clock_mismatch_rejected(self):
        t,a=fixture();t["actors"][0]["sides"][SHOES[0]]["samples"][20]["t_s"]+=.005;sign(t,a)
        with self.assertRaisesRegex(ValueError,"SHOE_CLOCK"):evaluate(t,a)
    def test_original_wrong_timestamp(self):
        t,a=fixture();a["actors"][0]["sides"]["L"][101]["time_s"]+=.1
        with self.assertRaisesRegex(ValueError,"SOURCE_CLOCK"):evaluate(t,a)
    def test_nonfinite_source(self):
        t,a=fixture();a["actors"][0]["sides"]["R"][2]["source_toe"][1]=math.nan
        with self.assertRaisesRegex(ValueError,"NONFINITE"):evaluate(t,a)
    def test_missing_target_shoe_partition(self):
        t,a=fixture();del t["actors"][0]["sides"][SHOES[0]];sign(t,a)
        with self.assertRaisesRegex(ValueError,"RIG_OR_SIDE"):evaluate(t,a)
    def test_forged_anatomical_mapping(self):
        d=evaluate(*fixture());d["actors"][0]["sides_anatomically_identified"]=True
        with self.assertRaisesRegex(ValueError,"CLOCK_OR_FALSE_ANATOMY"):independent(d)
    def test_forged_ground(self):
        d=evaluate(*fixture());d["source_floor_calibrated"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_CONTACT_OR_RELEASE"):independent(d)
    def test_forged_native(self):
        d=evaluate(*fixture());d["motion_physically_actuated"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_CONTACT_OR_RELEASE"):independent(d)
    def test_mvp_false_promotion(self):
        d=evaluate(*fixture());d["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_CONTACT_OR_RELEASE"):independent(d)
    def test_heldout_metric_finite(self):
        d=evaluate(*fixture())
        for a in d["actors"]:
            for c in a["comparisons"]:
                for s in c["sides"]:
                    self.assertTrue(math.isfinite(c["sides"][s]["train_fit"]["heldout_abs_p95_m"]))
if __name__=="__main__":unittest.main()
