import hashlib
import math
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from videoqa_kaggle_probe import EXPECTED_FIXTURE_SHA256, detect_accelerator, fixtures, source_bytes, cpu_scores, verify, run, validate_traces

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
        self.assertEqual(hashlib.sha256(data).hexdigest(), EXPECTED_FIXTURE_SHA256)
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


    def test_cpu_receipt_attests_own_code(self):
        import videoqa_kaggle_probe as probe
        receipt = run('cpu')
        self.assertEqual(receipt['executed_source_sha256'],
                         hashlib.sha256(Path(probe.__file__).read_bytes()).hexdigest())

    def test_direct_autodetect_tpu8(self):
        fake_jax = types.ModuleType('jax')
        fake_jax.default_backend = lambda: 'tpu'
        fake_jax.local_devices = lambda backend='tpu': list(range(8))
        with patch.dict(sys.modules, {'jax': fake_jax, 'torch': None}):
            self.assertEqual(detect_accelerator(), 'tpu')

    def test_direct_autodetect_cuda_t4x2(self):
        fake_jax = types.ModuleType('jax')
        fake_jax.default_backend = lambda: 'cpu'
        fake_torch = types.ModuleType('torch')
        fake_torch.cuda = types.SimpleNamespace(
            is_available=lambda: True,
            device_count=lambda: 2,
            get_device_name=lambda idx: 'Tesla T4')
        with patch.dict(sys.modules, {'jax': fake_jax, 'torch': fake_torch}):
            self.assertEqual(detect_accelerator(), 'gpu')

    def test_direct_autodetect_fail_closed_on_cpu(self):
        fake_jax = types.ModuleType('jax')
        fake_jax.default_backend = lambda: 'cpu'
        fake_torch = types.ModuleType('torch')
        fake_torch.cuda = types.SimpleNamespace(
            is_available=lambda: False,
            device_count=lambda: 0,
            get_device_name=lambda idx: 'CPU')
        with patch.dict(sys.modules, {'jax': fake_jax, 'torch': fake_torch}):
            with self.assertRaisesRegex(RuntimeError, 'NO_VERIFIED_ACCELERATOR'):
                detect_accelerator()

    def test_direct_autodetect_rejects_one_t4(self):
        fake_jax = types.ModuleType('jax')
        fake_jax.default_backend = lambda: 'cpu'
        fake_torch = types.ModuleType('torch')
        fake_torch.cuda = types.SimpleNamespace(
            is_available=lambda: True,
            device_count=lambda: 1,
            get_device_name=lambda idx: 'Tesla T4')
        with patch.dict(sys.modules, {'jax': fake_jax, 'torch': fake_torch}):
            with self.assertRaises(RuntimeError):
                detect_accelerator()

if __name__ == '__main__':
    unittest.main()
