import tempfile
import unittest
from forensic import ADMITTED,ISSUE_CODES,audit

class ResidualFourScienceControls(unittest.TestCase):
    def test_exact_authorized_four(self):
        self.assertEqual(set(ADMITTED),{
            "male_jump_slippers",
            "female_jumping_jacks_sandals",
            "female_cartwheel_barefoot",
            "male_diving_barefoot"})
    def test_reject_unknown_cases(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,"UNADMITTED_CASE"):
                audit(root,"male_stand_barefoot")
    def test_missing_original_media_never_guessed(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                audit(root,"male_jump_slippers")
    def test_research_findings_are_two_original_source_codes(self):
        self.assertEqual(ISSUE_CODES,{
            "LIMB_LENGTH_INVARIANT_VIOLATION",
            "LABELED_STANCE_FOOT_SLIDE"})
if __name__=="__main__":
    unittest.main()
