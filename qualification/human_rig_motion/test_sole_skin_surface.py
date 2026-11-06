#!/usr/bin/env python3
"""Pure-function adversarial calibration of original GLB footwear skin reader."""
import math
import unittest
from foot_anchor_support import InvalidModel
from sole_skin_surface import deform, ibm_position

IDENTITY=(1.,0.,0.,0., 0.,1.,0.,0., 0.,0.,1.,0., 0.,0.,0.,1.)
TRANSLATE_X_NEG2=(1.,0.,0.,0., 0.,1.,0.,0., 0.,0.,1.,0.,
                  -2.,0.,0.,1.)

def world(node,frame):
    return ((2.,3.,4.),(0.,0.,0.,1.))

class SurfaceSkinAdversarial(unittest.TestCase):
    def test_inverse_bind_homogeneous(self):
        self.assertEqual(ibm_position(IDENTITY,(1.,2.,3.)),(1.,2.,3.))
        self.assertEqual(ibm_position(TRANSLATE_X_NEG2,(2.,0.,0.)),(0.,0.,0.))

    def test_single_joint_world(self):
        self.assertEqual(deform((0.,0.,0.),(0,0,0,0),
                 (1.,0.,0.,0.),(3,), (IDENTITY,),world,0),
                 (2.,3.,4.))

    def test_inverted_bind_cancels_world_joint_translation(self):
        self.assertEqual(deform((2.,0.,0.),(0,0,0,0),
                 (1.,0.,0.,0.),(3,), (TRANSLATE_X_NEG2,),world,0),
                 (2.,3.,4.))

    def test_split_weights(self):
        def w(node,frame):
            return ((2.,0.,0.),(0.,0.,0.,1.)) if node==5 else (
                (4.,0.,0.),(0.,0.,0.,1.))
        self.assertEqual(deform((0.,0.,0.),(0,1,0,1),
             (.25,.25,.25,.25),(5,6),(IDENTITY,IDENTITY),w,0),
             (3.,0.,0.))

    def test_angular_source_world_projection(self):
        s=math.sqrt(.5)
        def w(node,frame):return ((0.,0.,0.),(s,0.,0.,s))
        v=deform((0.,1.,0.),(0,0,0,0),(1.,0.,0.,0.),
                 (0,),(IDENTITY,),w,0)
        self.assertAlmostEqual(v[1],0.,places=6)
        self.assertAlmostEqual(v[2],1.,places=6)

    def test_bad_world_homogeneous(self):
        m=list(IDENTITY);m[15]=0.
        with self.assertRaises(InvalidModel):
            ibm_position(tuple(m),(0.,0.,0.))

    def test_nonfinite_matrix(self):
        m=list(IDENTITY);m[7]=float("inf")
        with self.assertRaises(InvalidModel):
            ibm_position(tuple(m),(0.,0.,0.))

    def test_bad_skin_weights(self):
        for ws in ((1.1,-.1,0.,0.),(.2,.2,.2,.2),(float("nan"),0,0,0)):
            with self.assertRaises(InvalidModel):
                deform((0.,0.,0.),(0,0,0,0),ws,(0,),(IDENTITY,),world,0)

    def test_bad_joint_index(self):
        with self.assertRaises(InvalidModel):
            deform((0.,0.,0.),(1,0,0,0),(1.,0.,0.,0.),(0,),
                   (IDENTITY,),world,0)

    def test_no_input_mutation(self):
        p=(0.,1.,0.);j=(0,0,0,0);weights=(1.,0.,0.,0.)
        deform(p,j,weights,(0,),(IDENTITY,),world,0)
        self.assertEqual(p,(0.,1.,0.))
        self.assertEqual(weights,(1.,0.,0.,0.))

if __name__=="__main__":unittest.main()
