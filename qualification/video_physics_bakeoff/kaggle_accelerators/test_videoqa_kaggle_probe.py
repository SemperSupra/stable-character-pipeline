import math
import unittest
from videoqa_kaggle_probe import fixtures, source_bytes, cpu_scores, verify, run, validate_traces

class ResearchProbeTest(unittest.TestCase):
    def test_cpu_real_synthetic_metric(self):
        d = run('cpu')
        self.assertEqual(d['status'], 'PASS')
        self.assertEqual(d['verdicts'], ['PASS'] * 4 + ['FAIL'] * 4)
        self.assertEqual(d['device']['backend'], 'cpu')
        self.assertEqual(d['metric_scores'], [0] * 4 + [.2] * 4)
    def test_source_exact(self):
        data = source_bytes(fixtures())
        self.assertIn(b'scp.videoqa.kaggle-motion-probe.v1', data)
    def test_injected_score_rejected(self):
        with self.assertRaisesRegex(ValueError, 'METRIC_ORACLE_MISMATCH'):
            verify([0.] * 8, 'x', 'x')
    def test_bad_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_HASH_MISMATCH'):
            verify(cpu_scores(fixtures()), 'x', 'y')
    def test_short_trace_rejected(self):
        x = fixtures(); x[0].pop()
        with self.assertRaisesRegex(ValueError, '32'):
            validate_traces(x)
    def test_nonfinite_rejected(self):
        x = fixtures(); x[0][1][0] = math.nan
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            validate_traces(x)
    def test_wrong_backend_rejected(self):
        with self.assertRaisesRegex(ValueError, 'INVALID_BACKEND'):
            run('forged')

if __name__ == '__main__':
    unittest.main()
