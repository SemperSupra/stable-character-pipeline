"""Independent evidence-aggregate falsifiers for W9I clean-video HOG observations.

Designed to preserve first RED; reviewer never changes owning adjudicator.
"""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from test_adjudicate import fixtures
from adjudicate import adjudicate,CAMERAS

class AggregateReviewer(unittest.TestCase):
 def test_candidate_frame_count_not_trusted(self):
  args=fixtures()
  observed=args[7][CAMERAS[0]]
  observed["frames_with_candidates"]=24
  with self.assertRaisesRegex(ValueError,"W9_I_MODEL_AGGREGATE_MISMATCH"):
   adjudicate(*args)
 def test_more_than_two_count_not_trusted(self):
  args=fixtures()
  observed=args[7][CAMERAS[1]]
  observed["frames_with_more_than_two_candidates"]=24
  with self.assertRaisesRegex(ValueError,"W9_I_MODEL_AGGREGATE_MISMATCH"):
   adjudicate(*args)
 def test_unmodified_original_source_scope_remains_fail(self):
  args=fixtures()
  result=adjudicate(*args)
  self.assertEqual(result["overall"],"FAIL_FULLBODY_HUMAN_BEHAVIOR_PROXY_UNQUALIFIED")
  self.assertFalse(result["can_merge_release_deploy_or_promote"])
if __name__=="__main__":unittest.main()
