#!/usr/bin/env python3
import math
import unittest
from original_marker_visibility import DIM,SAMPLES,marker_signature

def fake_rgb(with_ring):
    data=bytearray(SAMPLES*DIM*DIM*3)
    if with_ring:
        for y in range(59,70):
            for x in range(59,70):
                i=(64*0 + y*DIM+x)*3
                data[i:i+3]=bytes((210,207,199))
    return bytes(data)

class MarkerControls(unittest.TestCase):
    def test_known_pale_fiducial_detected(self):
        result=marker_signature(fake_rgb(True),0,(64.,64.))
        self.assertTrue(result["fiducial_observed"])
        self.assertEqual(result["pale_pixels"],121)

    def test_blank_frame_cannot_be_visible(self):
        result=marker_signature(fake_rgb(False),0,(64.,64.))
        self.assertFalse(result["fiducial_observed"])
        self.assertEqual(result["pale_pixels"],0)

    def test_wrong_frame_count_rejected(self):
        with self.assertRaisesRegex(ValueError,"INVALID_DECODED_RGB"):
            marker_signature(bytes(8),0,(64.,64.))

    def test_nonfinite_projection_rejected(self):
        with self.assertRaisesRegex(ValueError,"INVALID_PROJECTION"):
            marker_signature(fake_rgb(True),0,(math.nan,64.))

if __name__=="__main__":
    unittest.main()
