import copy
import math
import unittest
from capture_order_ab import analyze
from test_pony52_actual_surface_native import measured
from test_pony_source_trajectory import fixture

def inputs():
    s=fixture()
    bp=measured(s,"physics");ba=measured(s,"animation")
    cp=copy.deepcopy(bp);ca=copy.deepcopy(ba)
    for r,ord in ((bp,"armature_then_capture"),(ba,"armature_then_capture"),
                  (cp,"capture_then_armature"),(ca,"capture_then_armature")):
        r["rest_capture_order"]=ord
        r["source_rest_order_experiment"]=True
        r["armature_index"]=0 if ord=="armature_then_capture" else 1
        r["rest_capture_index"]=1 if ord=="armature_then_capture" else 0
    return s,bp,ba,cp,ca

def improve(receipt,scale=.25):
    for frame in receipt["frames"]:
        f=frame["frame"]
        adjustment=.035*(1-scale)*math.sin(math.pi*(f-1)/47.)
        for row in frame["guides"]:
            row["tip_minus_root_m"][0]-=adjustment
            row["actual_tip_m"][0]-=adjustment

class ModifierOrderABTests(unittest.TestCase):
    def test_valid_but_no_benefit_keeps_existing_order(self):
        args=inputs()
        r=analyze(*args)
        self.assertEqual(r["candidate_research_verdict"],"REJECT_CANDIDATE_KEEP_EXISTING_ORDER")
        self.assertFalse(r["release_or_CPE_admission"])
        self.assertEqual(r["scientific_hold"],"KEEP")
        self.assertEqual(r,analyze(*args))
    def test_improvement_is_only_research_not_admission(self):
        s,bp,ba,cp,ca=inputs()
        improve(cp);improve(ca)
        r=analyze(s,bp,ba,cp,ca)
        self.assertEqual(r["candidate_research_verdict"],"POTENTIAL_SOURCE_RIGID_FIDELITY_IMPROVEMENT_NEEDS_SCIENCE")
        self.assertTrue(r["no_worse_follicle_attachment"])
        self.assertGreater(r["rigid_p95_relative_improvement_fraction"],.05)
        self.assertFalse(r["original_pony_body_collision_clearance"])
        self.assertFalse(r["production_groom_pin_changed"])
    def test_improved_shape_with_worse_root_must_reject(self):
        s,bp,ba,cp,ca=inputs()
        improve(cp);improve(ca)
        for receipt in (cp,ca):
            for frame in receipt["frames"]:
                for row in frame["guides"]:
                    row["actual_root_m"][0]+=.002
                    row["actual_tip_m"][0]+=.002
                    row["root_error_m"]=.002
        r=analyze(s,bp,ba,cp,ca)
        self.assertFalse(r["no_worse_follicle_attachment"])
        self.assertEqual(r["candidate_research_verdict"],"REJECT_CANDIDATE_KEEP_EXISTING_ORDER")
    def test_improved_shape_with_new_body_ray_crossing_rejected(self):
        s,bp,ba,cp,ca=inputs()
        improve(cp);improve(ca)
        cp["frames"][6]["guides"][0]["segment_surface_ray_hits"]=2
        r=analyze(s,bp,ba,cp,ca)
        self.assertFalse(r["no_increased_ray_candidates"])
        self.assertEqual(r["candidate_research_verdict"],"REJECT_CANDIDATE_KEEP_EXISTING_ORDER")
    def test_hostile_swapped_modes_or_order_are_rejected(self):
        base=inputs()
        variants=[
            lambda x:x[3].update(rest_capture_order="armature_then_capture"),
            lambda x:x[3].update(rest_capture_index=1),
            lambda x:x[4].update(source_rest_order_experiment=False),
            lambda x:x[1].update(source_blend_sha256="f"*64),
            lambda x:x[4]["frames"].pop(),
            lambda x:x[3]["frames"][1]["guides"][0].update(tip_to_body_nearest_m=float("nan")),
            lambda x:x[3].update(full_body_collision_accepted=True),
        ]
        for modify in variants:
            args=list(copy.deepcopy(base));modify(args)
            with self.subTest(change=str(modify)):
                with self.assertRaises((ValueError,KeyError)):analyze(*args)
if __name__=="__main__":unittest.main()
