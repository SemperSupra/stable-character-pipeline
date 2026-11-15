"""Independent original public model-response replay controls: no VLM inference."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score

FIXTURE = HERE / "fixtures" / "real_public_cpu_r033_43745064137.json"


class ReplayTests(unittest.TestCase):
    def fixture(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_actual_previous_public_run_preserves_output_format_red(self):
        got = score.score(self.fixture())
        self.assertEqual((got["strict_correct"], got["count"], got["format_failures"]), (2, 3, 1))
        self.assertEqual(got["rows"][0]["strict_parsed_answer"], "UNPARSEABLE")
        self.assertEqual(got["critical_false_approvals"], 0)
        self.assertEqual(got["occlusion_guesses_without_abstention"], 0)
        self.assertEqual(got["human_preference_or_consent"], "NOT_TESTED")
        self.assertEqual(got["source_media_hash_attestation"], "DECLARED_IN_ORIGINAL_RUN_NOT_REHASHED_BY_REPLAY")

    def test_no_post_hoc_single_letter_alias(self):
        d = self.fixture()
        for answer in ("Y.", "Y", "yes, because two arms", "YES NO", "YES\nUNKNOWN", "YES!", "true", '{"answer":"YES"}'):
            d["fixtures"][0]["model_answer"] = answer
            with self.subTest(raw=answer):
                got = score.score(d)
                self.assertEqual(got["rows"][0]["strict_parsed_answer"], "UNPARSEABLE")

    def test_valid_single_tokens_and_terminal_period(self):
        d = self.fixture()
        for answer in ("YES", "yes.", " YeS ", "Yes.\t"):
            d["fixtures"][0]["model_answer"] = answer
            with self.subTest(raw=answer):
                got = score.score(d)
                self.assertEqual(got["rows"][0]["strict_parsed_answer"], "YES")

    def test_unsafe_false_approval_separate_from_format(self):
        d = self.fixture()
        d["fixtures"][1]["model_answer"] = "YES."
        d["fixtures"][2]["model_answer"] = "yes"
        got = score.score(d)
        self.assertEqual(got["critical_false_approvals"], 2)
        self.assertEqual(got["occlusion_guesses_without_abstention"], 1)
        self.assertEqual(got["format_failures"], 1)

    def test_self_reported_correctness_does_not_override_raw_answer(self):
        d = self.fixture()
        d["fixtures"][0]["correct_on_source_known_fixture"] = True
        got = score.score(d)
        self.assertEqual(got["strict_correct"], 2)

    def test_duplicate_evidence_or_bad_digest_fails(self):
        d = self.fixture()
        d["fixtures"][2]["fixture"] = d["fixtures"][0]["fixture"]
        with self.assertRaisesRegex(ValueError, "INVALID_OR_DUPLICATE"):
            score.score(d)
        d = self.fixture()
        d["fixtures"][0]["image_sha256"] = "fake-sha"
        with self.assertRaisesRegex(ValueError, "UNBOUND_IMAGE"):
            score.score(d)

    def test_canonical_or_model_promotion_cannot_be_claimed(self):
        d = self.fixture()
        d["status"] = "APPROVED"
        with self.assertRaisesRegex(ValueError, "APPROVAL_CLAIM"):
            score.score(d)
        d = self.fixture()
        d["source_class"] = "private_admitted"
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_EVIDENCE_CLASS"):
            score.score(d)

    def test_json_duplicate_key_and_size_budget_fail(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text('{"schema":"a","schema":"b"}')
            with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
                score.load(p)
            p.write_text(" " * ((1 << 20) + 1))
            with self.assertRaisesRegex(ValueError, "EVIDENCE_SIZE_BUDGET"):
                score.load(p)

if __name__ == "__main__":
    unittest.main()
