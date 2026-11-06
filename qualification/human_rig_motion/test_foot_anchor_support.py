#!/usr/bin/env python3
"""Source-isolated adversarial pose algebra checks, no third-party photos."""
import math
import unittest
from foot_anchor_support import InvalidModel, add, norm, qmul, qrotate, node_tracks

class FootAnchorChecks(unittest.TestCase):
    def test_rotated_vector(self):
        s=math.sqrt(.5)
        p=qrotate((s,0.,0.,s),(0.,1.,0.))
        self.assertAlmostEqual(p[0],0.,places=6)
        self.assertAlmostEqual(p[1],0.,places=6)
        self.assertAlmostEqual(p[2],1.,places=6)

    def test_quaternion_sign_equivalence(self):
        s=math.sqrt(.5)
        self.assertEqual(tuple(round(v,6) for v in qrotate((s,0,0,s),(0,1,0))),
                         tuple(round(v,6) for v in qrotate((-s,0,0,-s),(0,1,0))))

    def test_nonunit_fails_closed(self):
        for bad in ((2.,0.,0.,0.),(0.,0.,0.,0.),(float("nan"),0,0,1)):
            with self.assertRaises(InvalidModel):
                norm(bad)

    def test_parent_rotation_and_child_translation(self):
        s=math.sqrt(.5)
        doc={"nodes":[{"name":"root","translation":[1.,2.,3.],
                       "rotation":[s,0.,0.,s],"children":[1]},
                      {"name":"child","translation":[0.,1.,0.]}],
             "animations":[{"channels":[],"samplers":[]}]}
        world=node_tracks(doc,b"")
        pos,q=world(1,0)
        self.assertAlmostEqual(pos[0],1.,places=6)
        self.assertAlmostEqual(pos[1],2.,places=6)
        self.assertAlmostEqual(pos[2],4.,places=6)

    def test_nonuniform_scale_fails_closed(self):
        doc={"nodes":[{"name":"scaled","scale":[1.,2.,1.]}],
             "animations":[{"channels":[],"samplers":[]}]}
        with self.assertRaises(InvalidModel):
            node_tracks(doc,b"")(0,0)

    def test_hierarchy_cycle_fails_closed(self):
        doc={"nodes":[{"name":"a","children":[1]},
                      {"name":"b","children":[0]}],
             "animations":[{"channels":[],"samplers":[]}]}
        with self.assertRaises(InvalidModel):
            node_tracks(doc,b"")

if __name__=="__main__":
    unittest.main()
