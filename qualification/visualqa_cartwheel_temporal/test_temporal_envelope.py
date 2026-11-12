"""Hostile and exact controls for cartwheel sampled-speed lower bound."""
import unittest
from temporal_envelope import (
    FRAME_COUNT, validate_intervals, exact_pairwise_min_speed,
    forward_intervals, reconstruct
)

class ReadOnlyTemporalEnvelopeTests(unittest.TestCase):
    def test_constant_pelvis_shift_requires_zero_sampled_speed(self):
        intervals=[[-.05,.10] for _ in range(FRAME_COUNT)]
        validate_intervals(intervals)
        bound,critical=exact_pairwise_min_speed(intervals)
        self.assertEqual(bound,0.)
        self.assertIsNone(critical)
        x=reconstruct(intervals,bound)
        self.assertEqual(len(x),FRAME_COUNT)
        self.assertTrue(all(v==0 for v in x))
    def test_abrupt_disjoint_holds_require_two_meters_per_second(self):
        intervals=[[0.,0.] for _ in range(20)]+[[.10,.10] for _ in range(20)]
        bound,critical=exact_pairwise_min_speed(intervals)
        self.assertAlmostEqual(bound,2.,places=8)
        self.assertEqual((critical["from_frame"],critical["to_frame"]),(19,20))
        self.assertIsNone(forward_intervals(intervals,1.99))
        path=reconstruct(intervals,bound)
        self.assertEqual(path[19],0.)
        self.assertEqual(path[20],.1)
    def test_long_range_endpoint_pair_can_be_limiting_constraint(self):
        intervals=[[0.,0.]]+[[0.,1.]]*38+[[1.,1.]]
        bound,critical=exact_pairwise_min_speed(intervals)
        self.assertAlmostEqual(bound,20./39.,places=10)
        self.assertEqual((critical["from_frame"],critical["to_frame"]),(0,39))
        self.assertIsNone(forward_intervals(intervals,bound-.001))
        self.assertEqual(len(reconstruct(intervals,bound+1e-9)),40)
    def test_nonfinite_and_bool_data_rejected(self):
        for value in (float("nan"),float("inf"),True):
            intervals=[[0.,.5] for _ in range(40)]
            intervals[5]=[value,.5]
            with self.assertRaises(ValueError):
                validate_intervals(intervals)
    def test_inverted_interval_and_missing_frames_rejected(self):
        for intervals in ([[0.,.5] for _ in range(39)],
                          [[1.,0.]]+[[0.,.5] for _ in range(39)]):
            with self.assertRaises(ValueError):
                validate_intervals(intervals)
    def test_no_negative_speed_admitted(self):
        with self.assertRaises(ValueError):
            forward_intervals([[0.,1.]]*40,-1)

if __name__=="__main__":
    unittest.main()
