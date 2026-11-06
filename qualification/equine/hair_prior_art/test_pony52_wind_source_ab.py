"""Hostile tests: original 4.5 skin-only source vs 5.2 wind-morph confound A/B."""
import copy
import math
import unittest
from pony52_wind_source_ab import quality
from test_pony52_actual_surface_native import measured
from test_pony_source_trajectory import fixture

def controls():
    source=fixture()
    variants=[]
    for treatment in ("animated","disabled"):
        pair=[]
        for mode in ("physics","animation"):
            r=measured(source,mode)
            r["source_wind_morph_mode"]=treatment
            r["source_wind_morphs_detected"]=9
            r["wind_keys_disabled_in_memory_only"]=treatment=="disabled"
            raw=[max(0.,.8*math.sin(math.pi*(j)/47)) for j in range(48)]
            r["source_wind_max_raw_activity_per_frame"]=raw[:]
            r["source_wind_max_activity_per_frame"]=raw[:] if treatment=="animated" else [0.]*48
            r["source_wind_f1_raw_before_override"]=0.
            if treatment=="disabled":
                # In this fixture the known mixed-in morph is precisely
                # .035*sin (which is absent from the skin-only reference).
                for k,fr in enumerate(r["frames"]):
                    shift=.035*math.sin(math.pi*k/47)
                    for row in fr["guides"]:
                        row["tip_minus_root_m"][0]-=shift
                        row["actual_tip_m"][0]-=shift
            pair.append(r)
        variants.extend(pair)
    return source,*variants

class ATests(unittest.TestCase):
    def test_known_wind_confound_removal_is_research_only(self):
        args=controls()
        r=quality(*args)
        self.assertEqual(r["verdict"],"SOURCE_WIND_MORPH_CONFOUND_BOUNDED_CONFIRMED_NO_NEW_RAY_CANDIDATES")
        self.assertTrue(r["source_wind_confound_corrected_to_skin_only_reference"])
        self.assertGreater(r["rigid_p95_relative_improvement_fraction"],.1)
        self.assertTrue(r["source_wind_control_raw_input_equivalent"])
        self.assertTrue(r["source_root_tracking_not_worse"])
        self.assertFalse(r["blender_52_production_upgrade_approved"])
        self.assertEqual(r["scientific_hold"],"KEEP")
        self.assertEqual(r,quality(*args))
    def test_no_activity_not_falsely_positive(self):
        args=list(controls())
        for r in args[1:]:
            r["source_wind_max_raw_activity_per_frame"]=[0.]*48
            if r["source_wind_morph_mode"]=="animated":
                r["source_wind_max_activity_per_frame"]=[0.]*48
        self.assertEqual(quality(*args)["verdict"],"INCONCLUSIVE_NO_SOURCE_WIND_ACTIVITY")
    def test_new_candidate_body_collision_disqualifies(self):
        args=list(controls())
        args[3]["frames"][10]["guides"][0]["segment_surface_ray_hits"]=4
        r=quality(*args)
        self.assertEqual(r["verdict"],"SOURCE_WIND_MORPH_CONFOUND_BOUNDED_CONFIRMED_COLLISION_HOLD")
        self.assertTrue(r["source_wind_confound_corrected_to_skin_only_reference"])
        self.assertGreater(r["body_ray_candidate_delta_by_region"]["mane"],0)
        self.assertTrue(r["source_consistency_separate_from_collision_admission"])
        self.assertFalse(r["body_ray_candidates_not_increased"])
    def test_forged_source_sha_modes_wind_and_science_holds_fail(self):
        baselines=controls()
        changes=[
            lambda a:a[1].update(source_blend_sha256="b"*64),
            lambda a:a[2].update(source_wind_morph_mode="disabled"),
            lambda a:a[3].update(wind_keys_disabled_in_memory_only=False),
            lambda a:a[4].update(source_wind_morphs_detected=8),
            lambda a:a[1]["source_wind_max_raw_activity_per_frame"].pop(),
            lambda a:a[3]["source_wind_max_activity_per_frame"].__setitem__(20,.2),
            lambda a:a[2]["source_wind_max_raw_activity_per_frame"].__setitem__(18,float("nan")),
            lambda a:a[4]["source_wind_max_activity_per_frame"].__setitem__(9,float("inf")),
            lambda a:a[3].update(release_admission=True),
            lambda a:a[2].update(science_hold="PASS"),
            lambda a:a[3]["frames"][8]["guides"][0].update(root_error_m=.1),
            lambda a:a[4]["frames"].pop(),
        ]
        for i,m in enumerate(changes):
            args=list(copy.deepcopy(baselines))
            m(args)
            with self.subTest(i=i):
                with self.assertRaises((ValueError,TypeError,KeyError)):
                    quality(*args)
if __name__=="__main__":unittest.main()
