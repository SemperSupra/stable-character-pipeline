import math
import unittest
from observe import D, EXPECTED, FRAME_IDS, marker_signature, project

class PixelSourceContractTests(unittest.TestCase):
    def test_empty_frame_not_false_pass(self):
        frame=bytes(D*D*3)
        result=marker_signature(frame,160,160)
        self.assertEqual(result["verdict"],"NOT_DETECTED")

    def test_positive_rendered_ring(self):
        frame=bytearray(D*D*3)
        for i in range(24):
            theta=2*math.pi*i/24
            x=round(160+10*math.cos(theta)); y=round(160+10*math.sin(theta))
            k=3*(y*D+x)
            frame[k:k+3]=bytes(EXPECTED)
        result=marker_signature(bytes(frame),160,160)
        self.assertEqual(result["verdict"],"DETECTED")
        self.assertEqual(result["angular_hits"],24)

    def test_frame_offscreen_abstains(self):
        self.assertEqual(marker_signature(bytes(D*D*3),2,160)["verdict"],"UNKNOWN")

    def test_camera_projection_rejects_nonfinite(self):
        with self.assertRaisesRegex(ValueError,"BAD_SOURCE_POINT"):
            project((1.0,float("nan"),1.0))

    def test_exact_frame_sampling(self):
        self.assertEqual(FRAME_IDS,(0,5,10,15,20,25,30,35))

if __name__=="__main__":
    unittest.main()
