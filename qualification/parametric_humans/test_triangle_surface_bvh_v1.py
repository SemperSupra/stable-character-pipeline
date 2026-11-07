"""Adversarial triangle contact tests, actual-body regression opt-in by explicit source."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
# Pure stdlib source-presence and qualification checks run even on unprovisioned CI.
class SourceContract(unittest.TestCase):
    def test_source_exists_and_is_scoped(self):
        s=(HERE/'triangle_surface_bvh_v1.py').read_text()
        for marker in ('SOURCE_SHA_MISMATCH','body_triangle_count','garment_triangle_count',
                       'no_triangle_crossing_proven','cloth_physics_qualified',
                       'native_blender_evaluated','release_approved'):
            self.assertIn(marker,s)
    def test_source_refuses_false_boolean_claims(self):
        s=(HERE/'triangle_surface_bvh_v1.py').read_text()
        for marker in ("'no_triangle_crossing_proven':False",
                       "'cloth_physics_qualified':False",
                       "'native_blender_evaluated':False",
                       "'wearable_fit_accepted':False"):
            self.assertIn(marker,s)

HAS_DEPS=all(importlib.util.find_spec(x) for x in ('numpy','vtk','scipy'))
if HAS_DEPS:
    import numpy as np
    import triangle_surface_bvh_v1 as bvh

@unittest.skipUnless(HAS_DEPS,'VTK/numpy/scipy required: local/native-only numerical witness')
class SyntheticContact(unittest.TestCase):
    def setUp(self):
        self.base=bvh.make_polydata([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]])
    def test_crossing_detected(self):
        other=bvh.make_polydata([[.25,.25,-1],[.25,.25,1],[.75,.75,0]],[[0,1,2]])
        self.assertGreater(bvh.contacts(self.base,other),0)
    def test_separated_rejected(self):
        far=bvh.make_polydata([[3,3,-1],[3,3,1],[4,4,0]],[[0,1,2]])
        self.assertEqual(bvh.contacts(self.base,far),0)
    def test_coplanar_not_accepted_as_separation(self):
        self.assertGreater(bvh.contacts(self.base,self.base),0)
    def test_out_of_bounds_and_duplicate_index_rejected(self):
        for faces in ([[0,1,3]],[[0,0,1]],[[1,2,-1]]):
            with self.subTest(faces=faces),self.assertRaises(bvh.ContactError):
                bvh.make_polydata([[0,0,0],[1,0,0],[0,1,0]],faces)
    def test_nan_rejected(self):
        with self.assertRaises(bvh.ContactError):
            bvh.make_polydata([[0,0,0],[1,0,float('nan')],[0,1,0]],[[0,1,2]])
    def test_frame_duplicate_and_invalid_rejected(self):
        for frames in (['rest','rest'],[-1],[72],[],['junk'],[0,0]):
            with self.subTest(frames=frames),self.assertRaises(bvh.ContactError):
                bvh._frames(frames)
    def test_source_sha_pin_rejected_before_geometry(self):
        with self.assertRaisesRegex(bvh.ContactError,'SOURCE_SHA_MISMATCH'):
            bvh.inspect(b'bad','0'*64,frames=['rest'])

@unittest.skipUnless(HAS_DEPS and bool(os.getenv('R009_MH35_GLB')), 'Exact original-only GLB not staged in public runner')
class ExactActualSource(unittest.TestCase):
    def test_vertex_zero_does_not_imply_triangle_zero(self):
        data=Path(os.environ['R009_MH35_GLB']).read_bytes()
        res=bvh.inspect(data,bvh.EXPECTED_SHA256,frames=['rest',16])
        self.assertEqual(res['frame_count'],2)
        self.assertEqual(set(res['actors']),set(bvh.ACTORS))
        self.assertTrue(res['any_crossings'])
        self.assertFalse(res['no_triangle_crossing_proven'])
        self.assertFalse(res['wearable_fit_accepted'])
        for actor in bvh.ACTORS:
            self.assertEqual(set(res['actors'][actor]['slots']),set(bvh.SLOTS))
            for slot in bvh.SLOTS:
                self.assertEqual(len(res['actors'][actor]['slots'][slot]),2)

if __name__=='__main__':unittest.main()
