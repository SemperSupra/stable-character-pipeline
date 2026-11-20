import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from source_contact import summarize
def source(length=60,velocity=0,above=.004):
 return [(i*velocity/60.,above,0.) for i in range(length)]
class SourceQual(unittest.TestCase):
 def test_static_near_minimum(self):
  x=summarize(source(60),1/60)
  self.assertGreater(x["slow_episode_count"],0)
  self.assertFalse(x["source_true_ground_contact_proven"])
 def test_full_skate(self):
  x=summarize(source(60,velocity=2.0),1/60)
  self.assertEqual(x["slow_episode_count"],0)
 def test_hover_near_self_min_is_not_ground(self):
  x=summarize(source(60,above=.5),1/60)
  self.assertFalse(x["source_true_ground_contact_proven"])
 def test_episodic(self):
  x=source(60)
  x=[(i/60.*3.,.1,0.) if i<30 else (1.5,.004,0.) for i in range(60)]
  self.assertGreater(summarize(x,1/60)["slow_episode_count"],0)
 def test_missing_samples(self):
  with self.assertRaisesRegex(ValueError,"SAMPLE_BOUNDS"):summarize(source(4),1/60)
 def test_nonfinite(self):
  x=source(60);x[5]=(math.nan,0,0)
  with self.assertRaisesRegex(ValueError,"SOURCE_POS"):summarize(x,1/60)
 def test_bad_clock(self):
  with self.assertRaisesRegex(ValueError,"CLOCK"):summarize(source(60),0)
 def test_no_false_contact(self):self.assertFalse(summarize(source(),1/60)["source_true_ground_contact_proven"])
if __name__=="__main__":unittest.main()
