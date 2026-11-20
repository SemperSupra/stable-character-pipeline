import unittest,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from lag import qualify
class Temporal(unittest.TestCase):
 def setUp(self):
  self.source=[(i*.04,math.sin(i*.17)) for i in range(143)]
 def test_zero_identical(self):
  x=qualify(self.source,self.source)
  self.assertEqual(x["best_train_lag"]["lag_samples"],0)
  self.assertEqual(x["zero_lag_baseline"]["heldout_root_rmse_m"],0)
 def test_shifted_clock(self):
  target=[self.source[min(142,i+5)] for i in range(143)]
  x=qualify(self.source,target)
  self.assertEqual(x["best_train_lag"]["lag_samples"],5)
 def test_nonzero_lag_can_overfit_train(self):
  target=[self.source[min(142,i+5)] if i<71 else self.source[i] for i in range(143)]
  x=qualify(self.source,target)
  self.assertEqual(x["best_train_lag"]["lag_samples"],5)
  self.assertGreater(x["best_train_lag"]["heldout_root_rmse_m"],0)
 def test_no_heldout_choice(self):
  x=qualify(self.source,self.source)
  self.assertTrue(x["heldout_result_was_not_used_to_choose_lag"])
 def test_bad_clock(self):
  with self.assertRaisesRegex(ValueError,"SOURCE_SAMPLE_CLOCK"):qualify(self.source,self.source[:50])
 def test_bad_bounds(self):
  with self.assertRaisesRegex(ValueError,"LEAKED_TRAIN_TEST"):qualify(self.source,self.source,train_end=81,test_start=70)
 def test_bad_lag(self):
  with self.assertRaisesRegex(ValueError,"LAG_BOUND"):qualify(self.source,self.source,lag_limit=24)
if __name__=="__main__":unittest.main()
