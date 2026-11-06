"""Hostile source-exact bare-5.2 vs original-4.5 vs attached-curve decomposition."""
import copy
import unittest
from test_pony_wind_state_interop import sample
from pony_wind_groom_transfer import compare,SCHEMA
from pony_source_trajectory import classify

def setup():
    skin,source45,rigid=sample()
    bare={"schema":SCHEMA,"source_kind":"original_synthetic",
        "source_blend_sha256":skin["source_blend_sha256"],
        "source_capsule_sha256":classify(skin)["source_capsule_sha256"],
        "rig":"PonyRig30","frame_count":48,"source_surface":"geometric_coat_mane_tail",
        "source_blender_version":"5.2.3","wind_names":source45["wind_names"][:],
        "frames":copy.deepcopy(source45["frames"]),
        "source_mutated_on_disk":False,"in_memory_groom_geometry_modified":False,
        "scientific_hold":"KEEP","release_admission":False}
    return skin,source45,bare,rigid

class StageTests(unittest.TestCase):
    def test_exact_source_and_curve_are_engineering_only(self):
        r=compare(*setup())
        self.assertEqual(r["verdict"],"SAMPLED_SOURCE_AND_CURVE_GEOMETRY_ALIGN_ENGINEERING_ONLY")
        self.assertTrue(r["full_nine_wind_channels_same_value_per_frame"])
        self.assertFalse(r["visual_accepted"])
        self.assertEqual(r["scientific_hold"],"KEEP")
        self.assertEqual(r,compare(*setup()))
    def test_bare_groom_version_drift_is_upstream(self):
        x=setup()
        for f in x[2]["frames"]:
            for g in f["guides"]:g["tip_m"][0]+=.04
        self.assertEqual(compare(*x)["verdict"],"UPSTREAM_52_BARE_SOURCE_GEOMETRY_DIFFERENT_SCIENCE_HOLD")
    def test_curve_transfer_error_is_separate(self):
        x=setup()
        for frame in x[3]["frames"]:
            for g in frame["guides"]:
                g["actual_tip_m"][0]+=.03
                g["tip_minus_root_m"][0]+=.03
        self.assertEqual(compare(*x)["verdict"],"SOURCE_GEOMETRY_EQUIVALENT_BUT_CURVE_TRANSFER_DIFFERS_SCIENCE_HOLD")
    def test_root_attachment_error_independent_from_tip(self):
        x=setup()
        for frame in x[3]["frames"]:
            for g in frame["guides"]:
                g["actual_root_m"][0]+=.03
                g["actual_tip_m"][0]+=.03
        self.assertEqual(compare(*x)["verdict"],"BOUNDARY_52_CURVE_ROOT_ATTACHMENT_DIFFERENT_SCIENCE_HOLD")
    def test_hostile_controls(self):
        changes=[
            lambda x:x[2].update(source_blend_sha256="f"*64),
            lambda x:x[2].update(source_observer_blender_version="4.5"),
            lambda x:x[2].update(source_blender_version="4.5.15"),
            lambda x:x[2].update(in_memory_groom_geometry_modified=True),
            lambda x:x[2].update(source_mutated_on_disk=True),
            lambda x:x[2].update(scientific_hold="PASS"),
            lambda x:x[2].update(release_admission=True),
            lambda x:x[2]["frames"].pop(),
            lambda x:x[2]["frames"][5].update(frame=4),
            lambda x:x[2]["frames"][5]["wind_weights"].__setitem__(1,.7),
            lambda x:x[2]["frames"][5]["guides"].pop(),
            lambda x:x[2]["frames"][5]["guides"][0].update(root_m=[float("nan"),0,0]),
            lambda x:x[2]["frames"][6]["guides"][0].update(card_id=999),
            lambda x:x[2]["frames"][2]["guides"][0].update(region="tail"),
            lambda x:x[3].update(release_admission=True)
        ]
        for i,fn in enumerate(changes):
            x=setup();fn(x)
            with self.subTest(i=i),self.assertRaises((ValueError,TypeError,KeyError)):compare(*x)

if __name__=="__main__":unittest.main()
