import hashlib
import math
import unittest
from cotracker_cpu import FRAMES,WIDTH,HEIGHT
from cotracker_robustness import PROFILES, ground_truth, truth_visible, frames, measure

class RobustnessProfileTest(unittest.TestCase):
    def test_three_profiles_included(self):
        self.assertEqual(PROFILES,('baseline','occluded','reversed_direction'))
    def test_all_profiles_are_original_deterministic(self):
        for name in PROFILES:
            a,b=frames(name),frames(name)
            self.assertEqual(hashlib.sha256(a).hexdigest(),hashlib.sha256(b).hexdigest())
            self.assertEqual(len(a),WIDTH*HEIGHT*FRAMES*3)
    def test_occlusion_does_not_change_true_trajectory(self):
        self.assertEqual(ground_truth('occluded'),ground_truth('baseline'))
        self.assertEqual(truth_visible('occluded').count(False),4)
    def test_occlusion_pixel_bytes_differ_only_as_defined(self):
        a=frames('baseline');b=frames('occluded')
        for t in range(FRAMES):
            start=t*WIDTH*HEIGHT*3
            self.assertEqual(a[start:start+WIDTH*HEIGHT*3]==b[start:start+WIDTH*HEIGHT*3],
                             not(4<=t<=7))
    def test_direction_reversal_has_negative_velocity(self):
        gt=ground_truth('reversed_direction')
        self.assertTrue(all(gt[i][0]-gt[i-1][0]==3 for i in range(1,6)))
        self.assertTrue(all(gt[i][0]-gt[i-1][0]==-3 for i in range(6,FRAMES)))
    def test_true_track_has_zero_error(self):
        for profile in PROFILES:
            p=ground_truth(profile)
            r=measure(profile,p,truth_visible(profile))
            self.assertEqual(r['ground_truth_visible_mae_px'],0.0)
    def test_false_occlusion_visibility_is_measured(self):
        p=ground_truth('occluded')
        r=measure('occluded',p,[True]*FRAMES)
        self.assertEqual(r['false_visible_during_occlusion'],4)
        self.assertEqual(r['visible_gt_frames'],FRAMES-4)
    def test_untracked_reappearance_is_not_an_unearned_pass(self):
        p=ground_truth('occluded')
        r=measure('occluded',p,[False]*FRAMES)
        self.assertIsNone(r['ground_truth_visible_mae_px'])
        self.assertEqual(r['missed_visible_frames'],FRAMES-4)
        self.assertEqual(r['acceptance'],'UNQUALIFIED_RESEARCH_OBSERVATION')
    def test_nonfinite_model_prediction_is_rejected(self):
        p=ground_truth('baseline')
        p[0]=(math.inf,60.)
        with self.assertRaisesRegex(ValueError,'INVALID_MODEL'):
            measure('baseline',p,[True]*FRAMES)
    def test_malformed_visibility_is_rejected(self):
        p=ground_truth('baseline')
        with self.assertRaisesRegex(ValueError,'INVALID_MODEL'):
            measure('baseline',p,[1]*FRAMES)

if __name__=='__main__':unittest.main()
