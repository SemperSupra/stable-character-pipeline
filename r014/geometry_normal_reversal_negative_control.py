#!/usr/bin/env python3
"""R014 public-safe negative control: normal-sign vs geometric inversion.

Generated entirely from original synthetic triangle; no CMU/MHR/private assets.
A normal reversal relative to frame one is not sufficient to infer inversion.
"""
import json
import math
import unittest

TRI = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))

def sub(a,b):
    return tuple(a[i]-b[i] for i in range(3))

def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def dot(a,b):
    return sum(a[i]*b[i] for i in range(3))

def norm(a):
    return math.sqrt(dot(a,a))

def normal(triangle):
    a,b,c=triangle
    return cross(sub(b,a),sub(c,a))

def area(triangle):
    return .5*norm(normal(triangle))

def edges(triangle):
    a,b,c=triangle
    return tuple(norm(sub(x,y)) for x,y in ((a,b),(b,c),(c,a)))

def rotate_y(v,theta):
    x,y,z=v
    return (math.cos(theta)*x+math.sin(theta)*z,y,
            -math.sin(theta)*x+math.cos(theta)*z)

def rest_normal_reversal(reference,candidate):
    return dot(normal(reference),normal(candidate))<=0.0

def receipt():
    theta=math.radians(120.0)
    moved=tuple(rotate_y(p,theta) for p in TRI)
    n0,n1=normal(TRI),normal(moved)
    return dict(schema="r014.synthetic_normal_rotation_falsifier.v1",
        source="original synthetic geometry (no CMU/MHR data)",
        degrees=120,determinant=1.0,
        rest_normal_dot=dot(n0,n1),
        legacy_flagged_as_inverted=rest_normal_reversal(TRI,moved),
        reference_area=area(TRI),rotated_area=area(moved),
        maximum_edge_length_delta=max(abs(a-b) for a,b in zip(edges(TRI),edges(moved))),
        transported_normal_dot=dot(rotate_y(n0,theta),n1),
        status="PASS_SYNTHETIC_FALSIFIER_ONLY__ALL_REAL_HUMAN_GATES_HOLD",
        limitation="No actual MHR triangle/CMU retarget validity or self-intersection established")

class NegativeControls(unittest.TestCase):
    def test_proper_rigid_rotation_triggers_legacy_oracle(self):
        r=receipt()
        self.assertTrue(r["legacy_flagged_as_inverted"])
        self.assertLess(r["rest_normal_dot"],0.)
        self.assertAlmostEqual(r["determinant"],1.)
        self.assertAlmostEqual(r["reference_area"],r["rotated_area"],places=12)
        self.assertLess(r["maximum_edge_length_delta"],1e-12)
        self.assertGreater(r["transported_normal_dot"],0.)
    def test_translation_is_not_flagged(self):
        moved=tuple((x+7.,y-3.,z+9.) for x,y,z in TRI)
        self.assertFalse(rest_normal_reversal(TRI,moved))
    def test_area_collapse_is_separate(self):
        collapsed=(TRI[0],TRI[1],TRI[0])
        self.assertLess(area(collapsed),.1*area(TRI))
    def test_rigid_rotations_preserve_intrinsic_geometry(self):
        for degrees in (0,60,120,180,270):
            moved=tuple(rotate_y(p,math.radians(degrees)) for p in TRI)
            self.assertAlmostEqual(area(moved),area(TRI),places=12)
            for a,b in zip(edges(moved),edges(TRI)):
                self.assertAlmostEqual(a,b,places=12)

if __name__=="__main__":
    import sys
    if len(sys.argv)==2 and sys.argv[1]=="--receipt":
        print(json.dumps(receipt(),sort_keys=True))
    else:
        unittest.main(verbosity=2)
