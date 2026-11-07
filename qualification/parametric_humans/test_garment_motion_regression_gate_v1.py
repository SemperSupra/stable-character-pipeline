"""Source-free deterministic adversarial controls for the 72-frame Pareto gate."""
import copy,unittest
from garment_motion_regression_gate_v1 import ACTORS,SLOTS,SCHEMA,RegressionError,compare

def fixture(sha='a'*64):
 row={'rest':0.0,'mean_72':.004,'max_72':.02,'frames_above_one_pct':8,'worst_frame':16}
 return {'schema':SCHEMA,'source_sha256':sha,'frames_per_actor':72,
  'native_blender':False,'triangle_collision_accepted':False,
  'visual_realism_accepted':False,'release_approved':False,
  'actors':{a:{s:copy.deepcopy(row) for s in SLOTS} for a in ACTORS}}
class GateTests(unittest.TestCase):
 def test_strict_nonregression_is_not_scientific_acceptance(self):
  a=fixture();b=fixture('b'*64)
  b['actors']['AsterOriginal']['costume_bottom']['max_72']=.01
  out=compare(a,b)
  self.assertEqual(out['verdict'],'PASS_RELATIVE_ONLY')
  self.assertFalse(out['cloth_fitting_accepted'])
  self.assertFalse(out['triangle_collision_qualified'])
 def test_reject_while_worst_improves_if_mean_worsens(self):
  a=fixture();b=fixture('b'*64)
  b['actors']['AsterOriginal']['costume_bottom']['max_72']=.01
  b['actors']['AsterOriginal']['costume_bottom']['mean_72']=.008
  out=compare(a,b)
  self.assertEqual(out['verdict'],'RED_REGRESSION')
  self.assertTrue(any('mean_72' in r['path'] for r in out['regressions']))
 def test_reject_new_rest_collision(self):
  a=fixture();b=fixture('b'*64)
  b['actors']['JuniperOriginal']['costume_bottom']['rest']=.005
  self.assertEqual(compare(a,b)['verdict'],'RED_REGRESSION')
 def test_reject_frequency_regression(self):
  a=fixture();b=fixture('b'*64)
  b['actors']['JuniperOriginal']['costume_bottom']['frames_above_one_pct']=10
  self.assertEqual(compare(a,b)['verdict'],'RED_REGRESSION')
 def test_reject_missing_actor(self):
  a=fixture();b=fixture('b'*64);del b['actors']['JuniperOriginal']
  with self.assertRaisesRegex(RegressionError,'ACTOR_SET_DRIFT'):compare(a,b)
 def test_reject_nan(self):
  a=fixture();b=fixture('b'*64);b['actors']['JuniperOriginal']['costume_top']['mean_72']=float('nan')
  with self.assertRaisesRegex(RegressionError,'BOUNDED_METRIC'):compare(a,b)
 def test_reject_approval_flag(self):
  a=fixture();b=fixture('b'*64);b['release_approved']=True
  with self.assertRaisesRegex(RegressionError,'FALSE_SCIENTIFIC_APPROVAL'):compare(a,b)
 def test_reject_same_source(self):
  a=fixture();b=copy.deepcopy(a)
  with self.assertRaisesRegex(RegressionError,'SAME_SOURCE_SHA'):compare(a,b)
 def test_hold_no_improvement(self):
  a=fixture();b=fixture('b'*64)
  self.assertEqual(compare(a,b)['verdict'],'HOLD_NO_IMPROVEMENT')

if __name__=='__main__':unittest.main()
