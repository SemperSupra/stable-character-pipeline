"""Offline source-authorized atlas citation and rights-provenance checks."""
import json
import pathlib
import unittest

ATLAS=pathlib.Path(__file__).with_name("research_sources.json")
class AtlasTests(unittest.TestCase):
    def test_no_unsourced_anatomical_number_promotion(self):
        obj=json.loads(ATLAS.read_text())
        self.assertEqual(obj["schema"],"scp.rom.provenance_atlas.v1")
        self.assertEqual(obj["authority_issue"],170)
        self.assertGreaterEqual(len(obj["records"]),10)
        self.assertEqual(obj["acceptance_policy"]["default_status"],"UNKNOWN_PROVENANCE_PENDING")
        ids=set()
        domains=set()
        for entry in obj["records"]:
            self.assertNotIn(entry["id"],ids)
            ids.add(entry["id"]);domains.add(entry["domain"])
            self.assertTrue(entry["source"].startswith("https://"))
            self.assertIsNone(entry["limit_values"],entry["id"])
            self.assertTrue(entry["readiness"])
        self.assertEqual(domains,{"human","animal","machine"})
    def test_substantial_model_context_schema(self):
        obj=json.loads(ATLAS.read_text())
        fields=set(obj["acceptance_policy"]["required_fields"])
        for name in ("taxon_or_mechanism","joint_anatomical_identity","axis_coordinate_system","loading_context",
                     "active_passive_rom","evidence_reference","data_license","independent_review"):
            self.assertIn(name,fields)
if __name__=="__main__":
    unittest.main()
