"""AJ/F1 original actual-mass stronger than vertical score, 8 negative controls."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from test_calibrate import fixture
from calibrate import evaluate
from f1_bridge import join,independent
def f1(aj):
    return {"schema":"scp.n03d-f1.native-shoe-foot-weights.v1",
            "source_scene_sha256":aj["source_scene_sha256"],
            "source_trace_sha256":aj["source_shoe_trace_sha256"],
            "anatomical_side_verified":False,"gait_contact_accepted":False,
            "mvp_accepted":False,"actors":[
                {"actor":name,"partitions":[
                    {"rest_local_partition":"rest_local_x_negative",
                     "candidate_rig_side":{"label":"R","dominance":1.},
                     "anatomical_foot_side_accepted":False},
                    {"rest_local_partition":"rest_local_x_positive",
                     "candidate_rig_side":{"label":"L","dominance":1.},
                     "anatomical_foot_side_accepted":False}]} for name in ("AsterOriginal","JuniperOriginal")
            ]}
def data():
    a=evaluate(*fixture())
    return a,f1(a)
class Reconciliation(unittest.TestCase):
    def test_f1_named_rig_authority_not_anatomy(self):
        a,b=data();v=join(a,b,"a"*64)
        self.assertEqual(independent(v),"HOLD")
        self.assertTrue(all(x["weight_based_named_rig_mapping"]=="REST_X_POS_IS_LEFT" for x in v["actors"]))
        self.assertTrue(all(not x["f1_anatomical_side_proven"] for x in v["actors"]))
    def test_num_best_is_not_f1_authority(self):
        a,b=data()
        for v in a["actors"]:
            v["comparisons"][0]["mean_heldout_abs_p95_m"]=1.
            v["comparisons"][1]["mean_heldout_abs_p95_m"]=0.
        out=join(a,b,"a"*64)
        self.assertFalse(out["actors"][0]["aj_height_residual_agrees_with_vertex_weights"])
        self.assertEqual(out["actors"][0]["weight_based_named_rig_mapping"],"REST_X_POS_IS_LEFT")
    def test_bad_source(self):
        a,b=data();b["source_scene_sha256"]="b"*64
        with self.assertRaisesRegex(ValueError,"F1_SOURCE_OR_ACCEPTANCE"):join(a,b,"a"*64)
    def test_missing_shoe_partition(self):
        a,b=data();b["actors"][0]["partitions"].pop()
        with self.assertRaisesRegex(ValueError,"F1_PARTITION_COUNT"):join(a,b,"a"*64)
    def test_duplicate_side(self):
        a,b=data();b["actors"][0]["partitions"][1]["candidate_rig_side"]["label"]="R"
        with self.assertRaisesRegex(ValueError,"F1_UNIQUE_NAMED_RIG_SIDES"):join(a,b,"a"*64)
    def test_no_weight_confirmation(self):
        a,b=data();b["actors"][0]["partitions"][0]["candidate_rig_side"]["dominance"]=.6
        with self.assertRaisesRegex(ValueError,"F1_RIG_LABEL_NOT_PROVEN"):join(a,b,"a"*64)
    def test_forged_contact(self):
        a,b=data();v=join(a,b,"a"*64);v["anatomical_ground_or_contact_proven"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_RIG_OR_CONTACT_ADMISSION"):independent(v)
    def test_false_mapping_tamper(self):
        a,b=data();v=join(a,b,"a"*64);v["actors"][0]["weight_based_named_rig_mapping"]="REST_X_NEG_IS_LEFT"
        with self.assertRaisesRegex(ValueError,"F1_MAPPING_SUBSTITUTION"):independent(v)
if __name__=="__main__":unittest.main()
