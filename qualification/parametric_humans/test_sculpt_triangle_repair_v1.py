import hashlib
import os
import unittest
from pathlib import Path
from sculpt_triangle_repair_v1 import repair,RepairError
from sculpt_topology_gate_v1 import inspect

class TestSourceFreeRepairs(unittest.TestCase):
    def test_wrong_hash_fails(self):
        with self.assertRaisesRegex(RepairError,'SOURCE_SHA256_MISMATCH'):
            repair(b'bad','0'*64)
    def test_missing_hash_fails(self):
        with self.assertRaisesRegex(RepairError,'SOURCE_SHA256_MISMATCH'):
            repair(b'bad','')
    def test_non_glb_fails(self):
        b=b'not a GLB'
        with self.assertRaises((ValueError,IndexError,KeyError,AssertionError)):
            repair(b,hashlib.sha256(b).hexdigest())

ROOT=Path(os.environ.get('SCP_SCULPT_QUALIFICATION_ROOT','/unavailable-private-source'))
SRC=ROOT/'sculpt_batch/output/r009_classic_adventurer_human_sculpt_v1_35joint.glb'
@unittest.skipUnless(SRC.exists(),'EXACT_SOURCE_CORPUS_NOT_LOCAL')
class TestActualSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=SRC.read_bytes()
        cls.sha=hashlib.sha256(cls.src).hexdigest()
        cls.after,cls.receipt=repair(cls.src,cls.sha)
    def test_equal_drop_for_both(self):
        for r in self.receipt['actors'].values():
            self.assertEqual(r['removed_zero_area_triangles'],144)
            self.assertFalse(self.receipt['human_anatomy_accepted'])
    def test_actual_no_zero_area_remains(self):
        r=inspect(self.after,hashlib.sha256(self.after).hexdigest())
        for x in r['actors'].values():
            self.assertEqual(x['degenerate_triangles_total'],0)
            self.assertGreater(x['body_component_count'],1)
    def test_rerun_byte_identical(self):
        again,_=repair(self.src,self.sha)
        self.assertEqual(again,self.after)

if __name__=='__main__':unittest.main()
