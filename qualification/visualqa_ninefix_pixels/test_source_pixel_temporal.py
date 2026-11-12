"""Dependency-free adversarial tests for source vs actual decoded pixel timing."""
import math
import unittest
from source_pixel_temporal import pixel_delta,pearson,rank_reviews,joint_velocity_series,FRAMES,FPS

def case_frames():
    frames=[]
    for i in range(FRAMES):
        frames.append({"frame":i,"time_s":i/FPS,
                       "joints":{"root":[float(i)/FPS,0.,1.],
                                 "head":[float(i)/FPS,0.,1.5]},
                       "contact":{"left":False,"right":False}})
    return {"schema":"scp.expanded-original-3d-motion-labels.v1",
            "case":"test", "fps":FPS,"frames":frames}

class PixelMotionControls(unittest.TestCase):
    def test_gray_same_frame_zero_motion(self):
        self.assertEqual(pixel_delta(bytes([0,255]),bytes([0,255])),0.)
    def test_gray_max_opposite_absolute_motion(self):
        self.assertEqual(pixel_delta(bytes([0,0,0]),bytes([255,255,255])),1.)
        self.assertAlmostEqual(pixel_delta(bytes([0,255]),bytes([255,255])),.5)
    def test_bad_frame_length_rejected(self):
        with self.assertRaises(ValueError):pixel_delta(b"a",b"aa")
        with self.assertRaises(ValueError):pixel_delta(b"",b"")
    def test_exact_source_40_frame_3d_clock(self):
        rates,count=joint_velocity_series(case_frames(),"test")
        self.assertEqual(count,2)
        self.assertEqual(len(rates),39)
        self.assertTrue(all(math.isclose(v,1.,abs_tol=1e-10) for v in rates))
    def test_nonfinite_source_fail_closed(self):
        f=case_frames()
        f["frames"][9]["joints"]["root"]=[float("nan"),0.,0.]
        with self.assertRaises(ValueError):joint_velocity_series(f,"test")
    def test_source_case_or_clock_not_invented(self):
        f=case_frames()
        with self.assertRaises(ValueError):joint_velocity_series(f,"other")
        f["frames"][6]["time_s"]+=.2
        with self.assertRaises(ValueError):joint_velocity_series(f,"test")
    def test_static_or_constant_series_abstain_correlation(self):
        self.assertIsNone(pearson([1.,1.,1.],[0.,1.,2.]))
        self.assertIsNone(pearson([0.,1.,2.],[0.,0.,0.]))
    def test_anticorrelation_detectable_without_false_grade(self):
        self.assertAlmostEqual(pearson([0.,1.,2.],[2.,1.,0.]),-1.,places=10)
    def test_review_list_only_reports_ranked_observations(self):
        r=rank_reviews([0.,1.,3.],[0.,.2,.01],top=2)
        self.assertEqual(len(r),2)
        self.assertEqual(r[0]["transition_end_frame"],3)
        self.assertTrue(all("uncalibrated_source_minus_video_rank" in x for x in r))
        self.assertTrue(all("verdict" not in x for x in r))

if __name__=="__main__":
    unittest.main()
