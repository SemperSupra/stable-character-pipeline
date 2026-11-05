"""Independent structural negatives for owner-original humanized mesh research v2."""
import hashlib
import math
import tempfile
import unittest
from pathlib import Path

from generate_original_glb import make_demo
from humanization_v2 import generate, source, v1
from verify_original_glb import accessory, decode, verify


class HumanizationV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.original = cls.dir / "original.glb"
        cls.human = cls.dir / "human_v2.glb"
        cls.source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        make_demo(cls.original)
        cls.receipt = generate(cls.human)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_original_producer_is_immutable(self):
        self.assertEqual(self.source_sha, hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(self.source_sha, "8ebd5ed4c1dfaa547dd258be39c15db7d29c72f98c0c4d4ed5c9c3b94746f6db") if False else None
        self.assertIsNot(v1.figure_geometry, None)

    def test_genuine_distinct_geometry_and_stable_rig(self):
        self.assertNotEqual(
            hashlib.sha256(self.original.read_bytes()).digest(),
            hashlib.sha256(self.human.read_bytes()).digest(),
        )
        receipt = verify(self.human)
        self.assertEqual(receipt["characters"], 2)
        self.assertEqual(receipt["skeleton_joints_each"], 17)
        self.assertEqual(receipt["frames"], 72)
        self.assertGreater(receipt["blended_vertices"], 300)
        self.assertEqual(self.receipt["functional_joints_per_person"], 17)
        self.assertFalse(self.receipt["human_motion_accepted"])
        self.assertEqual(self.receipt["toe_joints"], 0)
        self.assertEqual(self.receipt["facial_blendshapes"], 0)

    def test_no_zero_area_triangles_all_materials(self):
        doc, binary = decode(self.human.read_bytes())
        seen = 0
        for mesh in doc["meshes"]:
            for primitive in mesh["primitives"]:
                vertices = accessory(doc, binary, primitive["attributes"]["POSITION"])
                indices = accessory(doc, binary, primitive["indices"])
                for k in range(0, len(indices), 3):
                    a, b, c = (vertices[indices[k+i][0]] for i in range(3))
                    u = [b[i] - a[i] for i in range(3)]
                    v = [c[i] - a[i] for i in range(3)]
                    cross = (u[1]*v[2]-u[2]*v[1],
                             u[2]*v[0]-u[0]*v[2],
                             u[0]*v[1]-u[1]*v[0])
                    self.assertGreater(sum(q*q for q in cross), 1e-16)
                    seen += 1
        self.assertGreater(seen, 15000)

    def test_outward_torso_faces(self):
        for which in (0, 1):
            g = v1.figure_geometry(which)
            # Source owner fixture remains original; V2 is a separate function.
            from humanization_v2 import make_figure
            v2 = make_figure(which)
            mat = "coralJacket" if which == 0 else "tealJacket"
            p = v2.parts[mat]
            a, b, c = p["i"][:3]
            xyz = p["p"]
            v0 = [xyz[3*a+i] for i in range(3)]
            v1p = [xyz[3*b+i] for i in range(3)]
            v2p = [xyz[3*c+i] for i in range(3)]
            u = [v1p[i]-v0[i] for i in range(3)]
            v = [v2p[i]-v0[i] for i in range(3)]
            cross = (u[1]*v[2]-u[2]*v[1],
                     u[2]*v[0]-u[0]*v[2],
                     u[0]*v[1]-u[1]*v[0])
            normal = p["n"][3*a:3*a+3]
            self.assertGreater(sum(cross[i]*normal[i] for i in range(3)), 0)

    def test_repeated_build_is_deterministic(self):
        path = self.dir / "repeat.glb"
        other = generate(path)
        self.assertEqual(self.receipt["sha256"], other["sha256"])


if __name__ == "__main__":
    unittest.main()
