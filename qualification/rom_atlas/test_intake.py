"""Hostile natural/anatomical ROM evidence admission: no green biological values."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from intake import evaluate
ATLAS=json.loads(Path(__file__).with_name("research_sources.json").read_text())
SOURCE=b"original self-authored research extraction fixture - no normative values"
def sample():
    return {"schema":"scp.rom.anatomical_candidate.v1","candidate_id":"fixture-anat-hum-001",
            "domain":"human","taxon":"Homo sapiens","joint":"hip-flexion",
            "parent_bone":"pelvis","child_bone":"femur","axis_frame":"ISB_SOURCE_MAPPING_PENDING",
            "unit":"rad","measurement":"anatomical_joint_coordinate_convention_only",
            "context":"unloaded_model_only","active_passive":"model_only","cohort":"unspecified",
            "evidence_id":"human-jcs-2002","evidence_url":"https://pubmed.ncbi.nlm.nih.gov/11934426/",
            "source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC","reviewer":"unassigned",
            "review_state":"pending_independent_review","numeric_limits":None,
            "source_hash":hashlib.sha256(SOURCE).hexdigest()}
class CandidateTests(unittest.TestCase):
    def test_human_joint_frame_source_stays_unknown(self):
        r=evaluate(ATLAS,sample(),SOURCE)
        self.assertEqual(r["status"],"UNKNOWN_CANDIDATE_NOT_PRODUCTION_ADMITTED")
        self.assertFalse(r["can_promote"])
        self.assertEqual(r["human_animal_rom_acceptance"],"NOT_ACCEPTED")
    def test_unvalidated_biological_numbers_do_not_promote(self):
        m=sample();m["numeric_limits"]=[-.5,1.0]
        r=evaluate(ATLAS,m,SOURCE)
        self.assertIn("BIOLOGICAL_OR_ROBOT_NORMATIVE_LIMITS_NOT_INDEPENDENTLY_ADMITTED",r["issues"])
        self.assertEqual(r["status"],"UNKNOWN_CANDIDATE_NOT_PRODUCTION_ADMITTED")
    def test_canine_wrong_species_rejected(self):
        m=sample()
        m.update(domain="animal",taxon="Felis catus",evidence_id="dog-anatolian-goniometry",
                 evidence_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC13192051/")
        with self.assertRaisesRegex(ValueError,"WRONG_SPECIES_EVIDENCE"):
            evaluate(ATLAS,m,SOURCE)
    def test_rights_mismatch_rejected(self):
        m=sample();m["source_rights"]="SCRAPED_UNKNOWN_LICENSE"
        with self.assertRaisesRegex(ValueError,"SOURCE_LICENSE_NOT_ADMITTED"):
            evaluate(ATLAS,m,SOURCE)
    def test_changed_original_bytes_hash_rejected(self):
        m=sample()
        with self.assertRaisesRegex(ValueError,"SOURCE_ORIGINAL_BYTES_SHA"):
            evaluate(ATLAS,m,SOURCE+b"x")
    def test_reference_url_substitution_rejected(self):
        m=sample();m["evidence_url"]="https://evil.example.org"
        with self.assertRaisesRegex(ValueError,"ATLAS_SOURCE_NOT_MATCHED"):
            evaluate(ATLAS,m,SOURCE)
    def test_invalid_frame_or_wrong_parent_child_rejected(self):
        m=sample();m["axis_frame"]="unidentified"
        with self.assertRaisesRegex(ValueError,"COORDINATE_FRAME_OR_BONE_IDENTITY"):
            evaluate(ATLAS,m,SOURCE)
        m=sample();m["child_bone"]="pelvis"
        with self.assertRaisesRegex(ValueError,"COORDINATE_FRAME_OR_BONE_IDENTITY"):
            evaluate(ATLAS,m,SOURCE)
    def test_passive_vs_active_required(self):
        m=sample();m["active_passive"]="imprecise"
        with self.assertRaisesRegex(ValueError,"ROM_MEASUREMENT_MODE"):
            evaluate(ATLAS,m,SOURCE)
    def test_rejected_review_is_a_hard_veto(self):
        m=sample();m["review_state"]="rejected"
        self.assertEqual(evaluate(ATLAS,m,SOURCE)["status"],"FAIL_REVIEW_REJECTED")
    def test_no_invented_independent_approval(self):
        m=sample();m["review_state"]="approved"
        with self.assertRaisesRegex(ValueError,"REVIEW_STATE_NOT_ADMITTED"):
            evaluate(ATLAS,m,SOURCE)
    def test_bogus_numeric_ranges_rejected(self):
        m=sample();m["numeric_limits"]=[1,0]
        with self.assertRaisesRegex(ValueError,"NUMERIC_LIMITS_INVALID"):
            evaluate(ATLAS,m,SOURCE)
if __name__=="__main__":unittest.main()
