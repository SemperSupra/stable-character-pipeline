import hashlib
import math
import tempfile
import unittest
from source_pixel import (
    FRAMES,HEIGHT,WIDTH,project,source,render_rgb,encoded_decoded,
    corroborate,global_verdict,find_color,blank,circle,COLORS
)

class OriginalSourcePixelTest(unittest.TestCase):
    def test_source_is_exact_original_replay(self):
        x=source(False)
        self.assertEqual(len(x['frames']),FRAMES)
        self.assertEqual(x,source(False))
    def test_reversal_is_not_same_scene(self):
        self.assertNotEqual(source(True),source(False))
        self.assertEqual(source(True)['frames'][0],source(False)['frames'][0])
        self.assertNotEqual(source(True)['frames'][7],source(False)['frames'][7])
    def test_world_camera_projection(self):
        self.assertEqual(project([0,0,1]),(64,18))
        self.assertEqual(project([0,0,.5]),(64,68))
        self.assertEqual(project([.1,0,.05]),(80,113))
    def test_invalid_camera_calibration_is_error(self):
        with self.assertRaises(ValueError):project([0,.1,.5])
    def test_frame_lengths_deterministic(self):
        a=render_rgb(source(False))
        self.assertEqual(len(a),FRAMES*HEIGHT*WIDTH*3)
        self.assertEqual(hashlib.sha256(a).digest(),hashlib.sha256(render_rgb(source(False))).digest())
    def test_stale_source_fails_instead_of_explaining_away(self):
        actual=render_rgb(source(True))
        self.assertEqual(corroborate(source(False),actual)['verdict'],'FAIL')
    def test_correct_source_marker_pixels_agree(self):
        p=source(False)
        self.assertEqual(corroborate(p,render_rgb(p))['verdict'],'PASS')
    def test_missing_color_marker_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'MISSING'):
            find_color(blank(),'hip')
    def test_fail_dominates_alignment_pass(self):
        self.assertEqual(global_verdict('FAIL','PASS'),'FAIL')
        self.assertEqual(global_verdict('PASS','FAIL'),'FAIL')
    def test_unknown_is_not_success(self):
        self.assertEqual(global_verdict('UNKNOWN','PASS'),'UNKNOWN')
    def test_bogus_judge_is_error(self):
        with self.assertRaises(ValueError):global_verdict('ERROR','PASS')
    def test_native_h264_roundtrip_is_valid(self):
        with tempfile.TemporaryDirectory() as d:
            pose=source(False)
            clip,observed=encoded_decoded(pose,d,'test')
            self.assertTrue(clip.is_file())
            self.assertEqual(len(observed),len(render_rgb(pose)))
            self.assertEqual(corroborate(pose,observed)['verdict'],'PASS')

if __name__=='__main__':unittest.main()
