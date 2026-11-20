"""Hostile controls for source-conditioned gait onset and provenance."""
import copy
import math
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).parent))
from trace import evaluate, assess, first_bad_run

def fixtures(slide=True, onset=0):
    rows=[]
    for i in range(360):
        t=i/60
        foot=max(0,i-onset)/60 * .5 if slide else 0
        rows.append(dict(index=i,time_s=t,source_hip=[t*.5,.95,0],source_ankle=[0,.02,0],source_toe=[0,0,.1],
                         target_hip=[t*.5,0,.95],target_foot=[foot,0,.02],target_shoe_min_z=0))
    return rows

def document(rows=None):
    rows=rows or fixtures()
    return dict(schema="scp.n03d-ac.matched-source-to-bone-60hz.v1",source_class="ORIGINAL_FICTIONAL_CC0",
                source_motion_changed=False,mvp_accepted=False,
                actors=[dict(name=name,sides={"L":copy.deepcopy(rows),"R":copy.deepcopy(rows)})
                        for name in ("AsterOriginal","JuniperOriginal")])

class CausalControls(unittest.TestCase):
    def test_match_stationary(self):
        x=evaluate(fixtures(False))
        self.assertEqual(x["threshold_candidate_mismatch_count"],0)
        self.assertEqual(x["matched_target_foot_p50_mps"],0)
        self.assertEqual(x["status"],"HOLD")
    def test_slide_onset(self):
        x=evaluate(fixtures(True,onset=120))
        self.assertEqual(x["first_three_consecutive_source_candidate_target_slide"]["start_interval"],120)
        self.assertEqual(x["matched_source_ankle_p50_mps"],0)
        self.assertGreater(x["matched_target_foot_p50_mps"],0)
    def test_first_bad_run_does_not_binary_search_nonmonotone(self):
        self.assertEqual(first_bad_run([False,True,False,True,True,True,False,True,True,True]),(3,5))
    def test_exact_60hz(self):
        row=fixtures()
        row[80]["time_s"]+=.002
        with self.assertRaisesRegex(ValueError,"CLOCK_OR_INDEX"): evaluate(row)
    def test_nan(self):
        rows=fixtures();rows[2]["source_toe"][0]=math.nan
        with self.assertRaisesRegex(ValueError,"BAD_VECTOR"): evaluate(rows)
    def test_wrong_dim(self):
        rows=fixtures(); rows[0]["source_ankle"]=[0,0]
        with self.assertRaisesRegex(ValueError,"BAD_VECTOR"): evaluate(rows)
    def test_wrong_length(self):
        with self.assertRaisesRegex(ValueError,"SAMPLE_COUNT"): evaluate(fixtures()[:-1])
    def test_bad_source_rights(self):
        doc=document();doc["source_class"]="PRIVATE_NAOMI"
        with self.assertRaisesRegex(ValueError,"RIGHTS"): assess(doc)
    def test_forged_success(self):
        doc=document();doc["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_ACCEPTANCE_MUTATION"): assess(doc)
    def test_missing_side(self):
        doc=document();del doc["actors"][1]["sides"]["R"]
        with self.assertRaisesRegex(ValueError,"INCOMPLETE_FACTORIAL"): assess(doc)
    def test_duplicate(self):
        doc=document();doc["actors"][1]["name"]="AsterOriginal"
        with self.assertRaisesRegex(ValueError,"DUPLICATE_SIDE"): assess(doc)
    def test_zero_candidate_unknown(self):
        rows=fixtures()
        for row in rows:row["source_toe"][1]=0 if row["index"]%2==0 else .1
        x=evaluate(rows)
        self.assertEqual(x["candidate_interval_count"],0)
        self.assertIsNone(x["matched_target_foot_p50_mps"])
        self.assertEqual(x["causal_stage"],"UNKNOWN")
    def test_full_and_hold(self):
        result=assess(document())
        self.assertEqual(len(result["results"]),4)
        self.assertTrue(all(v["status"]=="HOLD" for v in result["results"]))
        self.assertFalse(result["mvp_accepted"])

if __name__=="__main__":
    unittest.main()
