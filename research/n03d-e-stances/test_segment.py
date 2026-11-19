import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from segment import analyze,threshold,hysteresis,viterbi,qualified_segments,STANCE,UNKNOWN
def samples(n=96,plant=((14,29),(53,74))):
 out=[]
 for i in range(n):
  contact=any(a<=i<b for a,b in plant)
  out.append({"t_s":i/24., "z_m":(.004+(i%3)*.0004) if contact else .095,
    "v_mps":(.008+(i%4)*.003) if contact else .65,
    "truth":contact})
 return out
class Qualification(unittest.TestCase):
 def test_clean_two_stances(self):
  s=samples()
  for fn in (threshold,hysteresis,viterbi):
   segments=qualified_segments(fn(s),s)
   self.assertGreaterEqual(len(segments),2)
 def test_no_stance_hover(self):
  s=samples(72,())
  for p in s:p["z_m"]=.06;p["v_mps"]=.0
  for fn in (threshold,hysteresis,viterbi):self.assertFalse(qualified_segments(fn(s),s))
 def test_no_stance_skating(self):
  s=samples(72,())
  for p in s:p["z_m"]=.004;p["v_mps"]=1.6
  for fn in (threshold,hysteresis,viterbi):self.assertFalse(qualified_segments(fn(s),s))
  self.assertEqual(len(analyze(s)["near_ground_skate_sample_indices"]),72)
 def test_single_spurious_does_not_admit(self):
  s=samples(72,());s[36]["z_m"]=0.;s[36]["v_mps"]=0.
  for fn in (threshold,hysteresis,viterbi):
   self.assertFalse(qualified_segments(fn(s),s))
 def test_gap_resets(self):
  s=samples(72,((15,40),));s[25]["z_m"]=None;s[25]["v_mps"]=None
  self.assertEqual(hysteresis(s)[25],UNKNOWN)
  self.assertFalse(any(z["first_index"]<=25<=z["last_index"] for z in qualified_segments(hysteresis(s),s)))
 def test_fail_nonfinite(self):
  s=samples();s[2]["v_mps"]=float("nan")
  with self.assertRaisesRegex(ValueError,"NONFINITE"):analyze(s)
 def test_fail_clock(self):
  s=samples();s[2]["t_s"]=s[1]["t_s"]
  with self.assertRaisesRegex(ValueError,"CLOCK_NONMONOTONIC"):analyze(s)
 def test_fail_negative_velocity(self):
  s=samples();s[4]["v_mps"]=-.1
  with self.assertRaisesRegex(ValueError,"OUT_OF_RANGE"):analyze(s)
 def test_gait_stays_unaccepted(self):
  self.assertFalse(analyze(samples())["actual_natural_gait_accepted"])
 def test_penetration_is_not_accepted(self):
  s=samples();s[20]["z_m"]=-.05
  self.assertIn(20,analyze(s)["penetration_over_10mm_sample_indices"])
 def test_missing_insufficient_telemetry(self):
  s=samples(15,());s[3]["z_m"]=None;s[3]["v_mps"]=None
  self.assertFalse(analyze(s)["algorithms"]["height_velocity"]["segmented_contact_evidence"])
if __name__=="__main__":unittest.main()
