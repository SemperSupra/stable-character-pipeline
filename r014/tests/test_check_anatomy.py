import json, unittest
from pathlib import Path
from r014.check_anatomy import assess

SCHEMA=json.loads((Path(__file__).parents[1]/"anatomical_coverage_v1.json").read_text())

class AnatomyCoverage(unittest.TestCase):
    def nominal(self):
        f={k:"PRESENT_VERIFIED" for k in SCHEMA["common_external"]}
        for variant in ("female","male"):
            f.update({k:"PRESENT_VERIFIED" for k in SCHEMA["external_reproductive_variants"][variant]})
        return {"id":"synthetic_test_fixture","age_class":"adult",
                "active_reproductive_variants":["female","male"],"features":f,
                "evidence":{k:"VERIFIED" for k in SCHEMA["required_model_evidence"]}}
    def test_manifest_positive_is_not_anatomy_pass(self):
        r=assess(SCHEMA,self.nominal())
        self.assertEqual(r["status"],"PASS_MANIFEST_ONLY")
        self.assertIn("No mesh, film, or tissue simulation evaluated",r["limits"])
    def test_no_genital_surface_fails_closed(self):
        x=self.nominal();del x["features"]["clitoral_glans"]
        self.assertIn("variant-geometry-unverified:female/clitoral_glans",assess(SCHEMA,x)["errors"])
    def test_missing_scrotum_fails_closed(self):
        x=self.nominal();x["features"]["scrotal_skin"]="ABSENT"
        self.assertEqual(assess(SCHEMA,x)["status"],"HOLD_UNVERIFIED")
    def test_underage_subject_rejected(self):
        x=self.nominal();x["age_class"]="minor"
        self.assertIn("adult-only requirement unverified",assess(SCHEMA,x)["errors"])
    def test_no_variant_rejected(self):
        x=self.nominal();x["active_reproductive_variants"]=[]
        self.assertIn("no-external-anatomy-variant-declared",assess(SCHEMA,x)["errors"])
    def test_no_rights_receipt_rejected(self):
        x=self.nominal();del x["evidence"]["source_rights_manifest"]
        self.assertEqual(assess(SCHEMA,x)["status"],"HOLD_UNVERIFIED")

if __name__=="__main__":unittest.main()
