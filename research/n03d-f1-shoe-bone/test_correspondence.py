import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from correspondence import choose_side
class WeightJoin(unittest.TestCase):
 def test_source_left(self):self.assertEqual(choose_side({"L":100.,"R":1.})["label"],"L")
 def test_source_right(self):self.assertEqual(choose_side({"L":1.,"R":100.})["label"],"R")
 def test_ambiguous(self):self.assertEqual(choose_side({"L":51.,"R":49.})["label"],"UNKNOWN")
 def test_missing(self):self.assertEqual(choose_side({"L":0.,"R":0.})["reason"],"NO_ACTUAL_FOOT_WEIGHT")
 def test_no_forged_side(self):
  with self.assertRaisesRegex(ValueError,"INVALID"):choose_side({"L":20.,"Z":0.})
 def test_no_negative(self):
  with self.assertRaisesRegex(ValueError,"BAD"):choose_side({"L":-4.,"R":11.})
 def test_all_source_label_nonanatomical(self):self.assertEqual(choose_side({"L":100.,"R":1.})["reason"],"CANDIDATE_SOURCE_RIG_SIDE_NOT_ANATOMICAL")
if __name__=="__main__":unittest.main()
