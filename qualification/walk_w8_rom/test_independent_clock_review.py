"""Reviewer-only evidence clock falsifier; expected first RED on W8 owner source."""
import hashlib
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from test_crosswalk import fixture
from crosswalk import audit

class W8IndependentClockReviewer(unittest.TestCase):
 def test_fps_denominator_mutation_must_block(self):
  source_raw,receipt,native,sole=fixture("forward")
  source=json.loads(source_raw)
  source["fps_den"]=2
  changed=(json.dumps(source,sort_keys=True)+"\n").encode()
  digest=hashlib.sha256(changed).hexdigest()
  receipt["source_sha256"]=digest
  native["source_sha256"]=digest
  with self.assertRaisesRegex(ValueError,"W8_SOURCE_PROFILE_CLOCK"):
   audit(changed,receipt,native,sole)
 def test_original_synthetic_scope_preserves_biological_unknown(self):
  r=audit(*fixture("forward"))
  self.assertEqual(r["biological_jcs"],"UNKNOWN_NO_SOURCE_APPROVED_ANATOMICAL_FRAME")
  self.assertEqual(r["R009_product"],"HELD")
if __name__=="__main__":unittest.main()
