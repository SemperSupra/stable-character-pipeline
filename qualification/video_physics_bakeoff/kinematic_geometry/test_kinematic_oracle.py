import unittest
from kinematic_oracle import analyze


def sample():
    return {'schema': 'scp.gait-geometry.v1', 'approved_bend_pole': [0, 1, 0],
            'segment_lengths_m': [0.5, (0.1**2 + 0.45**2)**0.5],
            'frames': [{'time_s': i / 12, 'hip': [0, 0, 1], 'knee': [0, 0, 0.5], 'ankle': [0.1, 0, 0.05]} for i in range(5)]}


class GeometryTest(unittest.TestCase):
    def test_approved_bend(self):
        self.assertEqual(analyze(sample())['status'], 'PASS')

    def test_backward_knee(self):
        c = sample()
        c['frames'][3]['ankle'][0] = -0.1
        self.assertIn('REVERSED_KNEE_BEND', [i['code'] for i in analyze(c)['findings']])
        self.assertEqual(analyze(c)['status'], 'FAIL')

    def test_wrong_length(self):
        c = sample()
        c['frames'][2]['knee'][2] += 0.07
        self.assertIn('SEGMENT_LENGTH_VIOLATION', [i['code'] for i in analyze(c)['findings']])

    def test_straight_abstains(self):
        c = sample()
        c['frames'][2]['ankle'] = [0, 0, 0.5 - (0.1**2 + 0.45**2)**0.5]
        self.assertEqual(analyze(c)['status'], 'UNKNOWN')

    def test_degenerate_observed_fails(self):
        c = sample()
        c['frames'][2]['knee'] = c['frames'][2]['hip'][:]
        self.assertEqual(analyze(c)['status'], 'FAIL')

    def test_missing_calibration_hard_failure(self):
        c = sample()
        del c['approved_bend_pole']
        with self.assertRaises(ValueError):
            analyze(c)

    def test_nan_hard_failure(self):
        c = sample()
        c['frames'][2]['knee'][1] = float('nan')
        with self.assertRaises(ValueError):
            analyze(c)

    def test_repeated_frame_clock_hard_failure(self):
        c = sample()
        c['frames'][2]['time_s'] = c['frames'][1]['time_s']
        with self.assertRaises(ValueError):
            analyze(c)

    def test_speed_spike(self):
        c = sample()
        c['frames'][2]['knee'][0] = 0.7
        self.assertIn('KNEE_SPEED_SPIKE', [i['code'] for i in analyze(c)['findings']])


if __name__ == '__main__':
    unittest.main()
