import hashlib
import os
import unittest
from pathlib import Path
from sculpt_topology_gate_v1 import inspect,compare,TopologyError,SCHEMA,ACTORS

class TestIndependentTopologyContract(unittest.TestCase):
    def test_source_digest_mismatch(self):
        with self.assertRaisesRegex(TopologyError,'SOURCE_SHA256_MISMATCH'):
            inspect(b'raw','0'*64)
    def test_digest_pin_required(self):
        with self.assertRaisesRegex(TopologyError,'MISSING_SOURCE_SHA256'):
            inspect(b'raw','')
    def test_compare_reject_wrong_schema(self):
        with self.assertRaisesRegex(TopologyError,'BAD_RECEIPT_SCHEMA'):
            compare({'schema':'wrong'},{'schema':'wrong'})
    def test_compare_fails_on_missing_actor(self):
        with self.assertRaisesRegex(TopologyError,'MISSING_ACTOR'):
            compare({'schema':SCHEMA,'actors':{}},{'schema':SCHEMA,'actors':{}})
    def test_non_glb_expected_hash(self):
        raw=b'not a GLB'
        with self.assertRaises((ValueError,IndexError,KeyError,AssertionError)):
            inspect(raw,hashlib.sha256(raw).hexdigest())

# Actual original GLBs and derived sculpt outputs stay in Drive, never public Git.
ROOT=Path(os.environ.get('SCP_SCULPT_QUALIFICATION_ROOT','/unavailable-private-source'))
ORIG=ROOT/'wardrobe_batch/artifacts/r009_classic_adventurer_aster_juniper_35joint.glb'
SCULPT=ROOT/'sculpt_batch/output/r009_classic_adventurer_human_sculpt_v1_35joint.glb'
@unittest.skipUnless(ORIG.exists() and SCULPT.exists(),'EXACT_SOURCE_CORPUS_NOT_LOCAL')
class TestRealSourceTopology(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=inspect(ORIG.read_bytes(),hashlib.sha256(ORIG.read_bytes()).hexdigest())
        cls.new=inspect(SCULPT.read_bytes(),hashlib.sha256(SCULPT.read_bytes()).hexdigest())
    def test_measured_components_improve_but_not_accept(self):
        d=compare(self.old,self.new)
        for a in ACTORS:
            row=d['actors'][a]
            self.assertGreater(row['component_reduction'],0)
            self.assertGreater(row['after_body_components'],1)
            self.assertFalse(row['realistic_anatomy_accepted'])
        self.assertFalse(d['visual_approval'])
    def test_morphology_technical_hold(self):
        self.assertEqual(self.new['finding'],'DISCONNECTED_BODY_COMPONENTS_REMAIN')
        self.assertEqual(self.new['native_blender_evaluated_frames'],0)
        self.assertFalse(self.new['realistic_anatomy_accepted'])

if __name__=='__main__':unittest.main()
