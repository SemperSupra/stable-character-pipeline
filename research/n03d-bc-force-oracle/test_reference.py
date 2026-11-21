"""BC hostile OpenSim source header, temporal, kinematics and fake cross-trial contact controls."""
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from reference import parse_storage,interpolate,read_model,independent,evaluate,COMMIT
def sto(columns,rows,declared_cols=None):
    return ("test\nnRows="+str(len(rows))+"\nnColumns="+str(declared_cols or len(columns))+
        "\ninDegrees=no\nendheader\n"+"\t".join(columns)+"\n"+
        "\n".join("\t".join(str(v) for v in a) for a in rows)+"\n")
def fake_data(mismatch=False):
    cols=["time","ground_force_r_vy","ground_force_l_vy"]
    forced=[[i/60,700. if i<30 else 0.,700. if i>=25 else 0.] for i in range(120)]
    grf=parse_storage(sto(cols,forced))
    cj=["time"]+[
      "/jointset/walker_knee_r/knee_angle_r/value",
      "/jointset/walker_knee_l/knee_angle_l/value",
      "/jointset/ankle_r/ankle_angle_r/value",
      "/jointset/ankle_l/ankle_angle_l/value"]
    co=parse_storage(sto(cj,[[i/60]+[.1,.15,.2,.25] for i in range(120)],6 if mismatch else None))
    model={"model_name":"subject_walk_scaled","model_components":{"Body":20,"Coordinate":20}}
    assets={k:{"original_git_blob":"a"*40,"sha256":"b"*64,"bytes":5000} for k in ("force","coordinates","model")}
    return grf,co,model,assets
class Cases(unittest.TestCase):
    def test_true_reference_source_window(self):
        d=evaluate(*fake_data())
        self.assertEqual(independent(d),"HOLD")
        self.assertTrue(d["upstream_metadata_all_columns_consistent"])
        self.assertTrue(d["source_contact_known_only_for_this_walk"])
    def test_header_column_source_red_not_falsified(self):
        d=evaluate(*fake_data(True))
        self.assertEqual(independent(d),"HOLD")
        self.assertFalse(d["upstream_metadata_all_columns_consistent"])
        self.assertEqual(d["status"],"HOLD_SOURCE_COORDINATE_HEADER_MISMATCH")
        self.assertEqual(d["coordinates_metadata"]["observedcolumns"],"5")
    def test_absent_ground_data(self):
        a,b,c,d=fake_data()
        a["columns"][1]="force_unknown"
        with self.assertRaisesRegex(ValueError,"GRF_Y_FORCE_CHANNEL_MISSING"):evaluate(a,b,c,d)
    def test_unmatched_timeline(self):
        a,b,c,d=fake_data()
        b["rows"]=[[x[0]+10]+x[1:] for x in b["rows"]]
        with self.assertRaisesRegex(ValueError,"NO_TIME_OVERLAP"):evaluate(a,b,c,d)
    def test_bad_monotonic(self):
        with self.assertRaisesRegex(ValueError,"STORAGE_TIME_NOT_STRICT"):
            parse_storage(sto(["time","x"],[[i/60,1] for i in range(60)]+[[.2,1]]))
    def test_infinite_force(self):
        with self.assertRaisesRegex(ValueError,"STORAGE_NONFINITE_OR_WIDTH"):
            parse_storage(sto(["time","x"],[[i/60,math.inf if i==20 else 1.] for i in range(60)]))
    def test_truncated_storage(self):
        with self.assertRaisesRegex(ValueError,"HEADER_ROWS"):
            parse_storage(sto(["time","x"],[[i/60,1.] for i in range(60)]).replace("nRows=60","nRows=61"))
    def test_forged_source_crosscontact(self):
        d=evaluate(*fake_data());d["100style_or_MPF_source_contact_corroborated"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_SOURCE_CONTACT_TRANSFER"):independent(d)
    def test_forged_private_release(self):
        d=evaluate(*fake_data());d["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_SOURCE_CONTACT_TRANSFER"):independent(d)
    def test_force_identity(self):
        d=evaluate(*fake_data())
        r=d["vertical_grf_threshold_N_sensitivity"]["20"]
        self.assertAlmostEqual(r["right_stance_fraction"]+r["left_stance_fraction"]-
                               r["double_support_fraction"]+r["no_support_fraction"],1,places=4)
    def test_wrong_force_symmetry(self):
        d=evaluate(*fake_data());d["vertical_grf_threshold_N_sensitivity"]["20"]["double_support_fraction"]=.99
        with self.assertRaisesRegex(ValueError,"INVALID_BINARY_CONTACT_IDENTITY"):independent(d)
    def test_force_interpolates(self):
        a,b,c,d=fake_data()
        z=interpolate(.25,a["columns"].index("ground_force_r_vy"),a)
        self.assertEqual(z,700.)
    def test_bad_model(self):
        with self.assertRaisesRegex(ValueError,"MODEL_NAME"):
            read_model('<?xml version="1.0"?><OpenSimDocument><Model name="foo"/></OpenSimDocument>')
    def test_reference_commit_guard(self):
        d=evaluate(*fake_data());d["exact_commit"]="0"*40
        with self.assertRaisesRegex(ValueError,"FALSE_SOURCE_CONTACT_TRANSFER"):independent(d)
if __name__=="__main__":unittest.main()
