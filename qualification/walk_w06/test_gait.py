"""Public synthetic W06 source-clock, IK and contact falsifiers."""
from copy import deepcopy
import math
import unittest
from gait import ACTORS,FPS,N,generate,validate

class WalkingContract(unittest.TestCase):
    def setUp(self):
        self.normal=generate("relaxed")
        self.brisk=generate("brisk")

    def test_both_profiles_and_distinct_approach(self):
        for m in (self.normal,self.brisk):
            result=validate(m)
            self.assertEqual((result["characters"],result["frame_count"]),(2,72))
            self.assertLess(result["contact_slip_max_scene_units"],1e-7)
            self.assertLess(result["segment_length_max_residual_scene_units"],2e-7)
            self.assertGreaterEqual(result["minimum_root_separation_scene_units"],1.5)
        self.assertNotEqual(self.normal["frames"][-1]["actors"][ACTORS[0]["id"]]["root_x"],
                            self.brisk["frames"][-1]["actors"][ACTORS[0]["id"]]["root_x"])

    def test_continuous_foot_contact(self):
        lock=0
        for a,b in zip(self.normal["frames"],self.normal["frames"][1:]):
            for c in ACTORS:
                for foot in ("left","right"):
                    old=a["actors"][c["id"]]
                    new=b["actors"][c["id"]]
                    if old["contact"][foot] and new["contact"][foot]:
                        self.assertLess(math.dist(old["joints"]["ankle_"+foot],
                                                  new["joints"]["ankle_"+foot]),1e-7)
                        lock+=1
        self.assertGreater(lock,80)

    def test_wrong_rights_rejected(self):
        m=deepcopy(self.normal);m["source_rights"]="unknown_vendor"
        with self.assertRaises(ValueError):validate(m)

    def test_bad_clock_rejected(self):
        m=deepcopy(self.normal);m["frames"][0]["timestamp_ms"]=1
        with self.assertRaises(ValueError):validate(m)

    def test_deleted_frame_rejected(self):
        m=deepcopy(self.normal);m["frames"].pop()
        with self.assertRaises(ValueError):validate(m)

    def test_nonfinite_rejected(self):
        m=deepcopy(self.normal);m["frames"][3]["actors"][ACTORS[0]["id"]]["joints"]["knee_left"][0]=float("nan")
        with self.assertRaises(ValueError):validate(m)

    def test_foot_skate_rejected(self):
        m=deepcopy(self.normal);m["frames"][1]["actors"][ACTORS[0]["id"]]["joints"]["ankle_left"][0]+=.08
        with self.assertRaises(ValueError):validate(m)

    def test_stretched_leg_rejected(self):
        m=deepcopy(self.normal);m["frames"][8]["actors"][ACTORS[0]["id"]]["joints"]["knee_right"][1]+=.1
        with self.assertRaises(ValueError):validate(m)

    def test_collision_rejected(self):
        m=deepcopy(self.normal)
        for frame in m["frames"]:
            frame["actors"][ACTORS[1]["id"]]["root_x"]=frame["actors"][ACTORS[0]["id"]]["root_x"]
        with self.assertRaises(ValueError):validate(m)

    def test_missing_joint_rejected(self):
        m=deepcopy(self.normal)
        del m["frames"][4]["actors"][ACTORS[0]["id"]]["joints"]["head"]
        with self.assertRaises(ValueError):validate(m)

if __name__=="__main__":unittest.main()
