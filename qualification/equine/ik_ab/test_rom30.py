import copy,math,unittest
from rom30_metrics import evaluate,LINKS,FEET

class ROMThreeLink(unittest.TestCase):
 def fixture(self):
  points={}
  for foot in FEET:
   rows=[]
   for frame in range(1,49):
    links=[]
    for i,name in enumerate(LINKS[foot]):
     z=.8-.2*i
     links.append({'name':name,'head':(0,0,z),'tail':(0,0,z-.2)})
    rows.append({'frame':frame,'links':links})
   points[foot]=rows
  bones=set(n for row in LINKS.values() for n in row)|{f'extra_{i}' for i in range(18)}
  return points,bones
 def test_true_three_segment_constant_length(self):
  a,b=self.fixture();r=evaluate(a,b)
  self.assertEqual(r['failure_codes'],[])
  self.assertEqual(r['scientific_verdict'],'THREE_LINK_GUARDS_NO_FAILURE_BIOLOGICAL_UNKNOWN')
  self.assertFalse(r['animal_motion_accepted'])
 def test_length_drift_fails(self):
  a,b=self.fixture();a['front_L'][15]['links'][1]['tail']=(0,0,.35)
  r=evaluate(a,b)
  self.assertIn('front_L:actual_segment_length_drift',r['failure_codes'])
 def test_joint_gap_fails(self):
  a,b=self.fixture();a['hind_R'][3]['links'][2]['head']=(.1,0,.4)
  self.assertIn('hind_R:disconnected_joint_centers',evaluate(a,b)['failure_codes'])
 def test_missing_armature_refused(self):
  a,b=self.fixture()
  with self.assertRaises(ValueError):evaluate(a,b-{'front_R_lower'})
 def test_stale_source_nine_segment_report_refused(self):
  a,b=self.fixture();del a['front_R'][3]['links'][1]
  with self.assertRaises(ValueError):evaluate(a,b)
 def test_corrupted_frame_and_nonfinite_refused(self):
  a,b=self.fixture();a['front_L'][15]['frame']=4
  with self.assertRaises(ValueError):evaluate(a,b)
  a,b=self.fixture();a['front_L'][15]['links'][0]['tail']=(0,float('nan'),.3)
  with self.assertRaises(ValueError):evaluate(a,b)
 def test_legacy_composite_is_not_rigid_link(self):
  # Demonstrate why 2-link upper.tail->lower.tail can shrink even if
  # intermediate and lower actual 20cm bones each remain rigid.
  straight=math.dist((0,0,.6),(0,0,.2))
  bent=math.dist((0,0,.6),(.2,0,.4))
  self.assertGreater(straight-bent,.02)
if __name__=='__main__':unittest.main()
