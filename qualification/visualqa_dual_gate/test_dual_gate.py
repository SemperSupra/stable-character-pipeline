"""Hostile fixtures protect fail-closed Visual QA source+video gate."""
import copy
import unittest
from dual_gate import combine, targeted_gate

def fixtures():
    statuses = ["PASS"]*18+["FAIL"]*3+["UNKNOWN"]
    vids = ["PASS"]*14+["FAIL"]*6+["UNKNOWN"]*2
    source = {"schema":"scp.motion-math-corpus-audit.v1", "case_count":22,
              "cases":[{"case":"case_%02d"%i, "status":s,
                        "source_sha256":"a"*64, "frames_checked":40, "defect_count":0}
                       for i,s in enumerate(statuses)]}
    video = {"schema":"scp.video-bakeoff-receipt.v1", "total":22,
             "matched":0, "discrepancies":0,
             "results":[{"id":"case_%02d_video"%i,"kind":"video","verdict":v,
                         "source_sha256":"b"*64,"expected":"","matches_oracle":False,
                         "findings":[]} for i,v in enumerate(vids)]}
    return source,video

class DualGateHostileTests(unittest.TestCase):
    def test_source_failure_cannot_be_overridden_by_video_pass(self):
        self.assertEqual(targeted_gate("FAIL","PASS"),"BLOCK_CORRECTIVE_RESEARCH")
        self.assertEqual(targeted_gate("PASS","FAIL"),"BLOCK_CORRECTIVE_RESEARCH")
    def test_unknown_cannot_be_greenwashed(self):
        self.assertEqual(targeted_gate("UNKNOWN","PASS"),"ABSTAIN_HUMAN_OR_INDEPENDENT_REVIEW")
        self.assertEqual(targeted_gate("PASS","UNKNOWN"),"ABSTAIN_HUMAN_OR_INDEPENDENT_REVIEW")
    def test_two_passes_still_do_not_accept_realism(self):
        self.assertEqual(targeted_gate("PASS","PASS"),"TARGETED_SOURCE_AND_VIDEO_PASS_ONLY")
    def test_qualified_22_case_shape_and_hold(self):
        a,b=fixtures()
        out=combine(a,b)
        self.assertEqual(out["case_count"],22)
        self.assertEqual(out["global_realism_verdict"],"NOT_QUALIFIED")
        self.assertFalse(any(x["human_motion_realism_accepted"] for x in out["cases"]))
        self.assertEqual(out["cases"][20]["targeted_gate"],"BLOCK_CORRECTIVE_RESEARCH")
    def test_missing_case_and_duplicate_fail_closed(self):
        a,b=fixtures()
        b["results"][0]["id"]="wrong_video"
        with self.assertRaisesRegex(ValueError,"IDENTITY_SET"):combine(a,b)
        a,b=fixtures()
        b["results"][0]["id"]=b["results"][1]["id"]
        with self.assertRaisesRegex(ValueError,"UNTRUSTWORTHY_VIDEO"):combine(a,b)
    def test_no_oracle_falsifier(self):
        a,b=fixtures()
        b["results"][0]["expected"]="PASS"
        with self.assertRaisesRegex(ValueError,"UNTRUSTWORTHY_VIDEO"):combine(a,b)
    def test_source_and_video_provenance_fail_closed(self):
        a,b=fixtures()
        a["cases"][0]["source_sha256"]="short"
        with self.assertRaisesRegex(ValueError,"UNTRUSTWORTHY_SOURCE"):combine(a,b)
        a,b=fixtures()
        b["results"][0]["source_sha256"]="not-a-hash"
        with self.assertRaisesRegex(ValueError,"UNTRUSTWORTHY_VIDEO"):combine(a,b)
    def test_wrong_counts_do_not_silently_update_baseline(self):
        a,b=fixtures()
        a["cases"][19]["status"]="PASS"
        with self.assertRaisesRegex(ValueError,"COUNTS_CHANGED"):combine(a,b)
    def test_corrupt_frame_count_rejected(self):
        a,b=fixtures()
        a["cases"][0]["frames_checked"]=39
        with self.assertRaisesRegex(ValueError,"SOURCE_FRAMES_INCOMPLETE"):combine(a,b)

if __name__=="__main__":
    unittest.main()
