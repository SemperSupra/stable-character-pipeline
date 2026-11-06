import copy
import math
import unittest
from challenge import challenge, EvidenceError

def fixture():
    rows=[]
    for view in ("side","oblique"):
        for frame in (12,24):
            for name,score in (("m060",.5),("zero",.9),("p060",.6)):
                rows.append({"camera":view,"frame":frame,"candidate":name,
                    "reference_sha256":("a" if view=="side" and frame==12 else
                                        "b" if view=="side" else
                                        "c" if frame==12 else "d")*64,
                    "baseline_iou":.6,"candidate_iou":score})
    return {"schema":"scp.native_multiview_neckfit.v1",
            "model_source_sha256":"f"*64,"reference_kind":"SYNTHETIC_SELF_RENDER",
            "external_photo_fit":"NOT_RUN","reasoning_model_inference":"NOT_RUN",
            "physical_anatomy":"UNKNOWN",
            "disposition":"ENGINEERING_MULTI_VIEW_FIT_PASS_SCIENCE_UNKNOWN",
            "camera_count":2,"frames":[12,24],
            "candidate_angles_radians":{"m060":-.6,"zero":0.,"p060":.6},
            "per_view_frame":rows,
            "mean_iou_by_candidate":{"m060":.5,"zero":.9,"p060":.6},
            "baseline_mean_iou":.6,"best_candidate":"zero",
            "measured_gain":.3}

class ChallengerEvidence(unittest.TestCase):
    def test_measurement_and_science_holds(self):
        o=challenge(fixture())
        self.assertEqual(o["decision"],"RULE_ONLY_SYNTHETIC_IMPROVEMENT_OBSERVED")
        self.assertAlmostEqual(o["mean_gain"],.3)
        self.assertEqual(o["actual_reasoning_actor_inference"],"NOT_RUN")
        self.assertFalse(o["model_promotion"])
    def test_forged_reality_claim(self):
        x=fixture();x["external_photo_fit"]="PASS"
        with self.assertRaises(EvidenceError):challenge(x)
    def test_forged_inference(self):
        x=fixture();x["reasoning_model_inference"]="PASS"
        with self.assertRaises(EvidenceError):challenge(x)
    def test_forged_score(self):
        x=fixture();x["mean_iou_by_candidate"]["zero"]=1.
        with self.assertRaisesRegex(EvidenceError,"aggregate"):challenge(x)
    def test_forged_baseline(self):
        x=fixture();x["baseline_mean_iou"]=.1
        with self.assertRaisesRegex(EvidenceError,"baseline mean"):challenge(x)
    def test_missing_view_frame(self):
        x=fixture();x["per_view_frame"].pop()
        with self.assertRaises(EvidenceError):challenge(x)
    def test_reference_swap(self):
        x=fixture();x["per_view_frame"][1]["reference_sha256"]="e"*64
        with self.assertRaisesRegex(EvidenceError,"reference"):challenge(x)
    def test_baseline_swap(self):
        x=fixture();x["per_view_frame"][1]["baseline_iou"]=.2
        with self.assertRaisesRegex(EvidenceError,"baseline"):challenge(x)
    def test_forged_best_candidate(self):
        x=fixture();x["best_candidate"]="p060"
        with self.assertRaisesRegex(EvidenceError,"winning"):challenge(x)
    def test_cross_view_regression_must_abstain(self):
        x=fixture()
        target=next(z for z in x["per_view_frame"] if z["camera"]=="oblique"
                    and z["frame"]==24 and z["candidate"]=="zero")
        target["candidate_iou"]=.55
        x["mean_iou_by_candidate"]["zero"]=(.9*3+.55)/4
        x["measured_gain"]=x["mean_iou_by_candidate"]["zero"]-.6
        self.assertEqual(challenge(x)["decision"],"ABSTAIN_NO_CROSS_VIEW_IMPROVEMENT")
    def test_nonfinite_fails_closed(self):
        for val in (math.nan,math.inf,-1.,1.01):
            x=fixture();x["per_view_frame"][0]["candidate_iou"]=val
            with self.assertRaises(EvidenceError):challenge(x)
    def test_duplicate_or_invalid_source(self):
        x=fixture();x["per_view_frame"][0]=copy.deepcopy(x["per_view_frame"][1])
        with self.assertRaises(EvidenceError):challenge(x)
        x=fixture();x["model_source_sha256"]="not a hash"
        with self.assertRaises(EvidenceError):challenge(x)

if __name__=="__main__":unittest.main()
