"""Independent R17 hostile component provenance evidence review.

Reviewer-only: creates no new licenses or original package SHA claims.
These falsifiers are expected RED until R14 source owner rejects duplicate
and malformed evidence property entries rather than silently dict-collapsing.
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"sbom_inventory"))
from test_observed import model
from r14_integrity import verify

class IndependentSupplyWitness(unittest.TestCase):
 def test_duplicate_component_property_is_denied(self):
  bom=model()
  p=bom["components"][0]["properties"]
  p.append(dict(p[0]))
  with self.assertRaisesRegex(ValueError,"COMPONENT_DUPLICATE_OR_MALFORMED_PROVENANCE"):
   verify(bom)
 def test_malformed_component_property_is_denied(self):
  bom=model()
  bom["components"][0]["properties"].append({"name":"scp:license-admission","value":"UNKNOWN_NOT_REVIEWED","unknown":"unreviewed-extra"})
  with self.assertRaisesRegex(ValueError,"COMPONENT_DUPLICATE_OR_MALFORMED_PROVENANCE"):
   verify(bom)
 def test_synthetic_observation_never_claims_supply_clearance(self):
  result=verify(model())
  self.assertEqual(result["supply_provenance"],"UNKNOWN_ORIGINAL_BINARY_AND_RIGHTS")
  self.assertTrue(result["status"].startswith("HOLD_"))
if __name__=="__main__":unittest.main()
