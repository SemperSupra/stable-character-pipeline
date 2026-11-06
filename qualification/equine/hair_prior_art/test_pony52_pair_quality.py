import copy
import math
import unittest
from test_pony_source_trajectory import fixture
from pony52_pair_quality import quality

def moving_source():
    s=fixture()
    for g in s["guides"]:
        for i,item in enumerate(g["samples"]):
            displacement=.16*i/47
            item["root_m"][0]+=(displacement)
            item["tip_m"][0]+=(displacement)
    return s

def measured(source,mode):
    items=[]
    for f in range(48):
        samples=[]
        for g in source["guides"]:
            root=g["samples"][f]["root_m"][:]
            d=[.0,0.,-.2]
            if mode=="physics":
                d[0]=.04*math.sin(math.pi*f/47)
            tip=[root[k]+d[k] for k in range(3)]
            samples.append({"card_id":g["card_id"],"region":g["region"],
                "root_world_m":root,"tip_world_m":tip,
                "source_root_m":root,"tip_minus_root_m":d[:],
                "source_skin_root_error_m":0.})
        items.append({"frame":f+1,"samples":samples})
    import pony_source_trajectory
    source_sha=pony_source_trajectory.classify(source)["source_capsule_sha256"]
    return {"schema":"equine.pony.xpbd_source_proxy_48f.v1",
        "source_capsule_sha256":source_sha,"source_blend_sha256":source["source_blend_sha256"],
        "source_rig":"PonyRig30","source_cards_total":1050,
        "mode":mode,"status":"SOURCE_48F_PROXY_GEOMETRY_MEASURED_NO_SCIENCE",
        "not_original_body_collision":True,
        "production_blender_4_5_15_untouched":True,"science_hold":"KEEP",
        "release_admission":False,"errors":[],"frame_count":48,"guide_count":6,
        "frames":items}
class QualityTests(unittest.TestCase):
    def test_original_trace_plus_rigid_negative_control(self):
        s=moving_source();a=measured(s,"physics");b=measured(s,"animation")
        r=quality(s,a,b)
        self.assertEqual(r["verdict"],"SOURCE_PONY_PROXY_SECONDARY_MOTION_ENGINEERING_ONLY")
        self.assertEqual(r["max_animation_control_delta_m_by_region"],{"mane":0.,"forelock":0.,"tail":0.})
        self.assertFalse(r["release_or_CPE_admission"])
        self.assertEqual(r["body_and_hair_collision"],"NOT_TESTED")
        self.assertGreater(r["max_actual_source_root_travel_m_by_region"]["tail"],.15)
        self.assertLess(r["max_tip_to_source_rest_strain_fraction_by_region"]["mane"],.10)
        self.assertTrue(r["science_warnings"])
        self.assertEqual(r,quality(s,a,b))
    def test_forged_or_incomplete_source_and_motion(self):
        s=moving_source();a=measured(s,"physics");b=measured(s,"animation")
        cases=[
            lambda x:x["frames"].pop(),
            lambda x:x["frames"][1]["samples"].pop(),
            lambda x:x["frames"][2]["samples"][0].update(card_id=750),
            lambda x:x["frames"][2]["samples"][0].update(source_root_m=[100.,100.,100.]),
            lambda x:x["frames"][2]["samples"][0].update(source_skin_root_error_m=.05),
            lambda x:x["frames"][2]["samples"][0].update(tip_minus_root_m=[0,0,0]),
            lambda x:x.update(source_blend_sha256="b"*64),
            lambda x:x.update(mode="animation"),
            lambda x:x.update(science_hold="PASS")
        ]
        for i,fn in enumerate(cases):
            with self.subTest(i=i):
                mutate=copy.deepcopy(a);fn(mutate)
                with self.assertRaises(ValueError):quality(s,mutate,b)
    def test_rigid_both_fail_closed(self):
        s=moving_source();b=measured(s,"animation");a=measured(s,"physics")
        for row in a["frames"]:
            for sample in row["samples"]:
                sample["tip_minus_root_m"]=[0,0,-.2]
                sample["tip_world_m"]=[sample["root_world_m"][0],sample["root_world_m"][1],sample["root_world_m"][2]-.2]
        with self.assertRaises(ValueError):quality(s,a,b)
    def test_overstrained_proxy_is_science_warning_not_acceptance(self):
        s=moving_source();a=measured(s,"physics");b=measured(s,"animation")
        for row in a["frames"][1:]:
            for sample in row["samples"]:
                sample["tip_minus_root_m"][2]=-.5
                sample["tip_world_m"][2]=sample["root_world_m"][2]-.5
        q=quality(s,a,b)
        self.assertIn("SOURCE_PROXY_GUIDE_STRAIN_OVER_10_PERCENT",q["science_warnings"])
        self.assertEqual(q["science_hold"],"KEEP")

    def test_control_accidental_motion_fails_closed(self):
        s=moving_source();a=measured(s,"physics");b=measured(s,"animation")
        for row in b["frames"][1:]:
            for sample in row["samples"]:
                sample["tip_minus_root_m"][0]+=.01
                sample["tip_world_m"][0]+=.01
        with self.assertRaises(ValueError):quality(s,a,b)
if __name__=="__main__":unittest.main()
