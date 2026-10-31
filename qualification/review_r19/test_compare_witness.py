import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from compare_witness import audit
def witness():
 return {"schema":"scp.r19.public_synthetic_blender_semantics.v1",
 "original_blend_sha256":"a"*64,"scene_semantic_sha256":"c"*64,"scene_semantic_bytes":100,
 "objects":8,"frames":24,"scope":"PUBLIC_ORIGINAL_SYNTHETIC_ONLY",
 "biomechanics":"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM",
 "human_behavior":"FAIL_ABSTRACT_LIMBS_ONLY","product":"HELD_R009_NOT_RUN_NOT_ADMITTED"}
class Review(unittest.TestCase):
 def test_equal_semantics_with_different_bytes_is_not_byte_determinism(self):
  a=witness();b=witness();b["original_blend_sha256"]="b"*64
  report=audit(a,b)
  self.assertFalse(report["binary_equal"])
  self.assertTrue(report["scene_semantic_equal"])
 def test_semantic_change_detected(self):
  a=witness();b=witness();b["original_blend_sha256"]="b"*64;b["scene_semantic_sha256"]="d"*64
  self.assertEqual(audit(a,b)["decision"],"FAIL_SCENE_SEMANTIC_DIVERGENCE")
 def test_forged_human_pass_denied(self):
  a=witness();b=witness();b["original_blend_sha256"]="b"*64;b["human_behavior"]="PASS"
  with self.assertRaisesRegex(ValueError,"SCIENTIFIC"):audit(a,b)
 def test_original_binary_equal_is_unexpected_input(self):
  with self.assertRaisesRegex(ValueError,"NONDETERMINISM"):audit(witness(),witness())
if __name__=="__main__":unittest.main()
