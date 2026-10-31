import copy
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from test_observed import model
from r14_integrity import verify

class SupplyIdentity(unittest.TestCase):
 def test_original_inventory_explicit_hold(self):
  x=verify(model())
  self.assertTrue(x["status"].startswith("HOLD_"))
  self.assertEqual(x["unverified_components"],159)
 def test_private_scope_mutation_rejected(self):
  b=model()
  for p in b["metadata"]["properties"]:
   if p["name"]=="scp:private-r009":p["value"]="ACCEPTED"
  with self.assertRaisesRegex(ValueError,"PRIVATE_RUNNER_OR_SOURCE_NOT_HELD"):verify(b)
 def test_source_identity_mutation_rejected(self):
  b=model();b["metadata"]["component"]["version"]="bad"
  with self.assertRaisesRegex(ValueError,"UNBOUND_GIT_SOURCE"):verify(b)
 def test_image_digest_mutation_rejected(self):
  b=model()
  for p in b["metadata"]["properties"]:
   if p["name"]=="scp:observed-local-image-id":p["value"]="sha256:invalid"
  with self.assertRaisesRegex(ValueError,"IMAGE_ID_NOT_PINNED"):verify(b)
 def test_unverified_component_claim_rejected(self):
  b=model();b["components"][0]["licenses"]=[{"license":{"id":"MIT"}}]
  with self.assertRaisesRegex(ValueError,"UNVERIFIED_RIGHTS_OR_BINARY_DIGEST_CLAIM"):verify(b)
 def test_missing_component_provenance_rejected(self):
  b=model();b["components"][0]["properties"]=[]
  with self.assertRaisesRegex(ValueError,"COMPONENT_SOURCE_ADMISSION_FORGED"):verify(b)
if __name__=="__main__":unittest.main()
