"""Adversarial/source immutability, all72 IK and true articulated-toe rig checks."""
import hashlib
import math
import tempfile
import unittest
from pathlib import Path
from humanization_v2 import generate
from rig35_v2 import main_expand
from phase_gait35 import animate,pose,leg,FRAMES,FPS
from test_rig35_v2 import witness
from verify_original_glb import decode,accessory

class PhaseGait35Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        root=Path(cls.tmp.name)
        cls.base=root/"original17.glb"
        cls.rig=root/"rig35.glb"
        cls.gait=root/"phase35.glb"
        generate(cls.base)
        main_expand(cls.base,cls.rig)
        cls.oldsha=hashlib.sha256(cls.rig.read_bytes()).hexdigest()
        cls.receipt=animate(cls.rig,cls.gait)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_input_immutable_and_output_skins(self):
        self.assertEqual(hashlib.sha256(self.rig.read_bytes()).hexdigest(),self.oldsha)
        self.assertNotEqual(self.gait.read_bytes(),self.rig.read_bytes())
        d1,_=decode(self.rig.read_bytes());d2,_=decode(self.gait.read_bytes())
        for section in ("meshes","skins","materials"):
            self.assertEqual(d1[section],d2[section],section)
        self.assertEqual(witness(self.gait)["frame_count"],72)
        self.assertEqual(self.receipt["rig_joints_each"],35)
        self.assertEqual(self.receipt["modified_animation_targets"],42)
        self.assertEqual(self.receipt["human_gait_acceptance"],"UNKNOWN_NOT_QUALIFIED")

    def test_toe_and_ankle_rotation_are_real_channels(self):
        d,b=decode(self.gait.read_bytes())
        targets={(d["nodes"][ch["target"]["node"]]["name"],ch["target"]["path"]):
                 ch["sampler"] for ch in d["animations"][0]["channels"]}
        for actor in ("AsterOriginal","JuniperOriginal"):
            for side in ("L","R"):
                for role in ("ankle","toe","ball","heel","clavicle"):
                    key=(actor+"_"+role+"_"+side,"rotation")
                    self.assertIn(key,targets)
                    sampler=d["animations"][0]["samplers"][targets[key]]
                    q=accessory(d,b,sampler["output"])
                    self.assertEqual(len(q),72)
                    self.assertTrue(all(abs(sum(v*v for v in t)-1)<1e-4 for t in q))
                    if role in ("toe","ball","ankle"):
                        self.assertGreater(max(x[0] for x in q)-min(x[0] for x in q),.015)

    def test_phase_and_contact_are_not_science(self):
        vals=[pose(i,0) for i in range(FRAMES)]
        self.assertTrue(any(v["legs"]["L"]["stage"]=="stance" for v in vals))
        self.assertTrue(any(v["legs"]["L"]["stage"]=="swing" for v in vals))
        self.assertTrue(all(math.isfinite(v["pelvis_delta"]) for v in vals))
        self.assertGreater(max(v["legs"]["L"]["angles"]["knee"] for v in vals)-
                           min(v["legs"]["L"]["angles"]["knee"] for v in vals),.25)

    def test_reject_wrong_parent_and_wrong_rig(self):
        with self.assertRaisesRegex(ValueError,"REQUIRES_EXACT_SOURCE_RIG35"):
            animate(self.base,Path(self.tmp.name)/"invalid.glb")

    def test_repeated_outputs_deterministic(self):
        second=Path(self.tmp.name)/"repeat-phase35.glb"
        animate(self.rig,second)
        self.assertEqual(self.gait.read_bytes(),second.read_bytes())

if __name__=="__main__":unittest.main()
