#!/usr/bin/env python3
import math
import unittest

from original_character_cotracker import FRAMES, ALLOWED, DIM, original_side_camera_project

class OriginalCharacterTrackingTests(unittest.TestCase):
    def test_explicit_frame_admission(self):
        self.assertEqual(FRAMES,tuple(range(0,36,3)))
        self.assertEqual(len(FRAMES),12)
        self.assertEqual(len(ALLOWED),4)

    def test_original_known_renderer_projected_ankle(self):
        point=original_side_camera_project((.10,-.14,0.))
        self.assertAlmostEqual(point[0],47.1,delta=.15)
        self.assertAlmostEqual(point[1],106.22,delta=.15)

    def test_reject_nonfinite_and_out_of_frame(self):
        for pt in ((math.nan,0.,0.),(1e8,0.,0.)):
            with self.assertRaises(ValueError):
                original_side_camera_project(pt)

if __name__=="__main__":
    unittest.main()
