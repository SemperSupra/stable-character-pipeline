"""Synthetic standalone falsifiers; genuine Blender 72f is verified in separate native job."""
import copy
import math
import unittest
from validate_receipt import validate, SOURCE, ZIP, NAMES

def fixture():
    observations = []
    for i in range(72):
        actors = []
        for j, name in enumerate(NAMES):
            start = -2.9 if j == 0 else 2.9
            end = -.9 if j == 0 else .9
            x = start + (end - start) * i / 71
            feet = {}
            for side in ("L", "R"):
                foot = [x, 0., .02]
                feet[side] = {
                    "toe_head_world_m": foot,
                    "toe_tail_world_m": foot,
                    "toe_tail_height_above_ground_m": .02,
                    "knee_interior_angle_deg_unqualified": 165.,
                }
            actors.append({
                "root": name, "root_world_m": [x, 0., 0.],
                "evaluated_mesh_min_z_m": -.002,
                "evaluated_mesh_min_clearance_m": -.002,
                "sampled_native_mesh_vertices": 4000,
                "feet": feet})
        observations.append({"frame": i, "actors": actors})
    return {
        "schema": "scp.mit_native_all72_foot_mesh_proxy.v1",
        "status": "NATIVE_OBSERVED_72F_FOOT_AND_SKIN_ONLY",
        "source_zip_sha256": ZIP,
        "source_blend_sha256": SOURCE,
        "source_mit": "WITH_NOTICE",
        "source_names": list(NAMES),
        "frame_count": 72, "fps": 12,
        "ground_surface_z_m": 0.,
        "root_separation_start_end_m": [5.8, 1.8],
        "observations": observations,
        "toe_ground_proximity_heuristics": {
            n: {s: {
                "near_ground_consecutive_frame_pairs_proxy_only": 71,
                "proxy_slide_gt_4cm_pairs": 0,
                "maximum_proxy_horizontal_step_m": 2/71,
            } for s in ("L", "R")} for n in NAMES},
        "foot_contact_accepted": False,
        "joint_coordinate_system_calibrated": False,
        "normative_biomechanics_accepted": False,
        "human_gait": "UNKNOWN",
        "product_accepted": False,
    }

class TestRigEvidence(unittest.TestCase):
    def deny(self, change):
        f = fixture()
        change(f)
        with self.assertRaises(ValueError):
            validate(f)
    def test_original_synthetic_shape_only(self):
        self.assertFalse(validate(fixture())["product_accepted"])
    def test_forged_product(self):
        self.deny(lambda x: x.__setitem__("product_accepted", True))
    def test_forged_contact(self):
        self.deny(lambda x: x.__setitem__("foot_contact_accepted", True))
    def test_forged_JCS(self):
        self.deny(lambda x: x.__setitem__("joint_coordinate_system_calibrated", True))
    def test_short_frames(self):
        self.deny(lambda x: x["observations"].pop())
    def test_reordered_frame(self):
        self.deny(lambda x: x["observations"][5].__setitem__("frame", 25))
    def test_fake_actor(self):
        self.deny(lambda x: x["observations"][0]["actors"][0].__setitem__("root", "forged"))
    def test_forged_blend_source(self):
        self.deny(lambda x: x.__setitem__("source_blend_sha256", "0"*64))
    def test_nonfinite_bone(self):
        self.deny(lambda x: x["observations"][0]["actors"][0]["feet"]["L"].__setitem__("knee_interior_angle_deg_unqualified", math.nan))
    def test_ground_arithmetic(self):
        self.deny(lambda x: x["observations"][0]["actors"][0].__setitem__("evaluated_mesh_min_clearance_m", 5.))
    def test_forged_ground_count(self):
        self.deny(lambda x: x["toe_ground_proximity_heuristics"][NAMES[0]]["L"].__setitem__("near_ground_consecutive_frame_pairs_proxy_only", 0))
    def test_forged_slide_count(self):
        self.deny(lambda x: x["toe_ground_proximity_heuristics"][NAMES[1]]["R"].__setitem__("proxy_slide_gt_4cm_pairs", 71))
    def test_forged_root_motion(self):
        self.deny(lambda x: x.__setitem__("root_separation_start_end_m", [5.8, 5.8]))
    def test_wrong_native_bone_weighted_mesh_count(self):
        self.deny(lambda x: x["observations"][0]["actors"][1].__setitem__("sampled_native_mesh_vertices", 0))

if __name__ == "__main__":
    unittest.main()
