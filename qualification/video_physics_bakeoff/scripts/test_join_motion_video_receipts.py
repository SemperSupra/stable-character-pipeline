#!/usr/bin/env python3
import hashlib
import unittest

from join_motion_video_receipts import triage, markdown

D = "a" * 64
V = "b" * 64

def fixtures():
    src_cases = [
        {"case":"s_pass_v_pass","status":"PASS","source_sha256":D,"findings":[]},
        {"case":"s_fail_v_pass","status":"FAIL","source_sha256":D,"findings":[{"code":"CONTACT"}]},
        {"case":"s_pass_v_fail","status":"PASS","source_sha256":D,"findings":[]},
        {"case":"s_unknown_v_pass","status":"UNKNOWN","source_sha256":D,"findings":[]},
    ]
    src = {"schema":"scp.motion-math-corpus-audit.v1","cases":src_cases,
           "case_count":len(src_cases),"counts":{"PASS":2,"FAIL":1,"UNKNOWN":1}}
    v_cases = []
    for case, verdict in zip(src_cases,("PASS","PASS","FAIL","PASS")):
        v_cases.append({"id":case["case"]+"_video","source_sha256":V,
                        "verdict":verdict,"expected":"","matches_oracle":False,
                        "findings":[],"metrics":{}})
    vid = {"schema":"scp.video-bakeoff-receipt.v1","results":v_cases,
           "total":4,"matched":0,"discrepancies":0}
    return src,vid

class JoinTests(unittest.TestCase):
    def test_true_modality_conflict_preserved(self):
        s,v=fixtures()
        data=triage(s,v,D,V)
        self.assertEqual(data["case_count"],4)
        self.assertEqual(data["dispositions"],{
            "INSUFFICIENT_TARGETED_EVIDENCE":1,
            "REJECT_TARGETED_CONTROLS":2,"TARGETED_CONTROLS_ONLY":1,
        })
        self.assertEqual(sum(x["modality_conflict"] for x in data["cases"]),2)
        self.assertIn("not an overall realism",markdown(data))

    def test_missing_video_fails_closed(self):
        s,v=fixtures()
        v["results"].pop()
        v["total"]=3
        with self.assertRaisesRegex(ValueError,"CASE_CUSTODY_MISMATCH"):
            triage(s,v,D,V)

    def test_gold_label_not_allowed(self):
        s,v=fixtures()
        v["results"][0]["expected"]="PASS"
        with self.assertRaisesRegex(ValueError,"VIDEO_GOLD_LABEL_OR_ERROR"):
            triage(s,v,D,V)

    def test_source_count_tamper_rejected(self):
        s,v=fixtures()
        s["counts"]["FAIL"]=0
        with self.assertRaisesRegex(ValueError,"SOURCE_COUNTS_DISAGREE"):
            triage(s,v,D,V)

    def test_duplicate_source_rejected(self):
        s,v=fixtures()
        s["cases"].append(s["cases"][0])
        s["case_count"]=5
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OR_INVALID_SOURCE_CASE"):
            triage(s,v,D,V)

if __name__=="__main__":
    unittest.main()
