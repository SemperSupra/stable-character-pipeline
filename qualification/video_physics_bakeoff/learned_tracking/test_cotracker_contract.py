import hashlib
import math
from pathlib import Path
import tempfile
import unittest

from cotracker_cpu import FRAMES, HEIGHT, WIDTH, adjudicate, decoded_h264, truth, video_rgb

class FirstRealModelContractTest(unittest.TestCase):
    def test_rights_original_frames(self):
        pixels=video_rgb()
        self.assertEqual(len(pixels),FRAMES*HEIGHT*WIDTH*3)
        self.assertEqual(pixels,video_rgb())
    def test_generated_centers_have_exact_speed(self):
        pts=truth()
        self.assertEqual(len(pts),FRAMES)
        self.assertTrue(all(pts[t][0]-pts[t-1][0]==3 for t in range(1,FRAMES)))
    def test_perfect_tracks_pass(self):
        v=adjudicate([[x,y] for x,y in truth()],[True]*FRAMES)
        self.assertEqual(v['gate'],'PASS')
        self.assertEqual(v['mae_px'],0.0)
    def test_bad_tracker_fails_without_claiming_model_failure(self):
        v=adjudicate([[24,60]]*FRAMES,[True]*FRAMES)
        self.assertEqual(v['gate'],'FAIL')
        self.assertGreater(v['mae_px'],5)
    def test_hidden_frames_abstain(self):
        v=adjudicate([[x,y] for x,y in truth()],[False]*FRAMES)
        self.assertEqual(v['gate'],'UNKNOWN')
    def test_forged_shape_rejected(self):
        with self.assertRaisesRegex(ValueError,'LENGTH'):
            adjudicate([[0,0]]*(FRAMES-1),[True]*FRAMES)
    def test_nonfinite_rejected(self):
        pts=[[x,y] for x,y in truth()]
        pts[3][1]=math.nan
        with self.assertRaisesRegex(ValueError,'NONFINITE'):
            adjudicate(pts,[True]*FRAMES)
    def test_nonboolean_visibility_rejected(self):
        with self.assertRaisesRegex(ValueError,'BOOLEAN'):
            adjudicate([[x,y] for x,y in truth()],[1]*FRAMES)
    def test_actual_codec_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            clip, raw=decoded_h264(d)
            self.assertEqual(len(raw),len(video_rgb()))
            self.assertNotEqual(hashlib.sha256(raw).hexdigest(),hashlib.sha256(video_rgb()).hexdigest())
            self.assertGreater(Path(clip).stat().st_size,1000)

if __name__=='__main__':unittest.main()
