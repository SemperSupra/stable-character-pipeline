"""Red/blue source-only controls for native original-skinned 5.2 attachment.

Articulated rigid strands MAY rotate in world coordinates. They must still
remain anchored at their own source follicle, and Physics must differ from the
rigid witness at identical frames. These are not collision acceptance tests.
"""
import copy
import math
import unittest
from pony52_actual_surface_native import evaluate_pair
from pony_source_trajectory import classify as source_classify
from test_pony_source_trajectory import fixture

def measured(source,mode):
    canonical=source_classify(source)
    frames=[]
    for index in range(48):
        samples=[]
        t=index/47.
        for guide in source["guides"]:
            root=guide["samples"][index]["root_m"]
            # Deliberate legal rigid WORLD rotation of a strand on articulated
            # head/tail/neck; zero same-frame nonrigid velocity is not required.
            control=[.035*math.sin(math.pi*t),0.,-.2]
            delta=[.07*math.sin(math.pi*t),0.,0.] if mode=="physics" else [0.,0.,0.]
            relative=[control[k]+delta[k] for k in range(3)]
            samples.append({
                "card_id":guide["card_id"],"region":guide["region"],
                "source_root_m":root[:],"actual_root_m":root[:],
                "actual_tip_m":[root[k]+relative[k] for k in range(3)],
                "tip_minus_root_m":relative[:],
                "root_error_m":0.,"tip_to_body_nearest_m":.02,
                "segment_surface_ray_hits":0,
                "curve_polyline_length_m":math.sqrt(sum(x*x for x in relative))*1.02})
        frames.append({"frame":index+1,"guides":samples})
    return {"schema":"equine.pony52.attached_original_groom_48f.v1",
        "mode":mode,"source_kind":"original_synthetic",
        "source_blend_sha256":source["source_blend_sha256"],
        "source_capsule_sha256":canonical["source_capsule_sha256"],
        "source_surface":"geometric_coat_mane_tail",
        "source_cards_total":1050,"source_bones":30,
        "source_surface_has_armature_skin":True,
        "curves_surface_binding_confirmed":True,
        "captured_rest_geometry":True,"surface_unique_anchor_uv":True,
        "modifier_mode":"Physics (Experimental)" if mode=="physics" else "Animation",
        "frame_count":48,"guide_count":6,"frames":frames,
        "errors":[],"science_hold":"KEEP","release_admission":False,
        "full_body_collision_accepted":False,
        "status":"48F_ORIGINAL_SKIN_GROOM_NATIVE_GEOMETRY_OBSERVED"}

class SourceAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.source=fixture()
        self.physics=measured(self.source,"physics")
        self.animation=measured(self.source,"animation")
    def test_articulated_rigid_rotation_valid_but_not_real_groom_admission(self):
        q=evaluate_pair(self.source,self.physics,self.animation)
        self.assertEqual(q["status"],"ATTACHED_ORIGINAL_SKIN_48F_ENGINEERING_PROOF_ONLY")
        self.assertGreater(q["max_rigid_world_space_rotation_displacement_m_by_region"]["mane"],.03)
        self.assertGreater(q["max_same_frame_physics_minus_animation_relative_tip_m_by_region"]["mane"],.06)
        self.assertFalse(q["release_admission"])
        self.assertFalse(q["full_anatomical_collision_clearance"])
        self.assertEqual(q,evaluate_pair(self.source,self.physics,self.animation))
    def test_two_same_frame_modes_not_a_physics_pass(self):
        p=copy.deepcopy(self.animation);p["mode"]="physics"
        p["modifier_mode"]="Physics (Experimental)"
        with self.assertRaises(ValueError):evaluate_pair(self.source,p,self.animation)
    def test_source_body_falsifiers_and_first_missing_frame(self):
        for modifier in (
            lambda x:x["frames"].pop(),
            lambda x:x["frames"][6].update(frame=5),
            lambda x:x["frames"][5]["guides"][0].update(card_id=999),
            lambda x:x["frames"][5]["guides"][0].update(source_root_m=[0,0,0]),
            lambda x:x["frames"][5]["guides"][0].update(root_error_m=.04),
            lambda x:x["frames"][5]["guides"][0].update(actual_root_m=[0,0,100]),
            lambda x:x["frames"][5]["guides"][0].update(tip_to_body_nearest_m=float("nan")),
            lambda x:x["frames"][5]["guides"][0].update(segment_surface_ray_hits=-1),
            lambda x:x["frames"][5]["guides"][0].update(tip_minus_root_m=[0,0,-10]),
            lambda x:x.update(science_hold="PASS"),
            lambda x:x.update(full_body_collision_accepted=True),
            lambda x:x.update(curves_surface_binding_confirmed=False),
            lambda x:x.update(modifier_mode="Animation"),
        ):
            p=copy.deepcopy(self.physics);modifier(p)
            with self.subTest(change=str(modifier)):
                with self.assertRaises(ValueError):evaluate_pair(self.source,p,self.animation)
    def test_real_potential_contacts_remain_science_red(self):
        p=copy.deepcopy(self.physics)
        p["frames"][20]["guides"][0]["segment_surface_ray_hits"]=4
        p["frames"][20]["guides"][0]["tip_to_body_nearest_m"]=.001
        q=evaluate_pair(self.source,p,self.animation)
        self.assertEqual(q["potential_body_segment_ray_hits_by_region"]["mane"],4)
        self.assertIn("POTENTIAL_RIGGED_BODY_STRAND_INTERSECTIONS_RETAIN_SCIENCE_HOLD",q["warnings"])
        self.assertFalse(q["visual_acceptance"])
        self.assertFalse(q["full_anatomical_collision_clearance"])

if __name__=="__main__":unittest.main()
