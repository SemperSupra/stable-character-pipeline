"""Source-admitted optional original-only deterministic GLB gate.

Public free CI intentionally skips without owner-specific exact source inputs.
"""
from __future__ import annotations
import hashlib, json, os, unittest
from pathlib import Path

class OriginalOnlyGlbIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get('SCP_R009_ORIGINAL_GL_B') or not os.environ.get('SCP_R009_ORIGINAL_SOLE'):
            raise unittest.SkipTest('Owner-only original 35-joint GLB and exact sole evidence not on public CI')
    def test_source_provenance_and_determinism(self):
        from root_y_envelope_glb_v1 import derive
        from root_y_envelope_dual_gate_v1 import evaluate
        from verify_root_y_floor_trial_v1 import inspect
        raw=Path(os.environ['SCP_R009_ORIGINAL_GL_B']).read_bytes()
        sole_raw=Path(os.environ['SCP_R009_ORIGINAL_SOLE']).read_bytes()
        out1,receipt=derive(raw,sole_raw)
        out2,receipt2=derive(raw,sole_raw)
        self.assertEqual(out1,out2)
        self.assertEqual(receipt,receipt2)
        self.assertNotEqual(hashlib.sha256(raw).hexdigest(),hashlib.sha256(out1).hexdigest())
        after=inspect(out1,receipt['derived_sha256'])
        gate=evaluate(json.loads(sole_raw),receipt,after,sole_raw)
        self.assertEqual(gate['verdict'],'PASS_FLOOR_AND_CONTINUITY_PROXY_ONLY')
        self.assertFalse(gate['natural_gait_accepted'])
    def test_wrong_source_sha_rejected(self):
        from root_y_envelope_glb_v1 import derive
        from root_y_lipschitz_envelope_v1 import EnvelopeError
        raw=bytearray(Path(os.environ['SCP_R009_ORIGINAL_GL_B']).read_bytes())
        raw[-8]^=1
        sole_raw=Path(os.environ['SCP_R009_ORIGINAL_SOLE']).read_bytes()
        with self.assertRaises(EnvelopeError):derive(bytes(raw),sole_raw)
if __name__=='__main__':unittest.main()
