"""CPU skin/animation negative controls, source-bound frame quality witness."""
import hashlib, json, os, unittest
from pathlib import Path
import numpy as np
from observe_makehuman35_motion_v0 import (
  inspect,parents_of,skin_vertices,triangle_metrics, MOTION_SCHEMA)

CANDIDATE=Path(__file__).resolve().parent/'aster_juniper_makehuman35_candidate_v0.glb'

class TestNegative(unittest.TestCase):
    def test_double_parent_fail_closed(self):
        nodes=[{'children':[2]},{'children':[2]},{'name':'shared'}]
        with self.assertRaisesRegex(ValueError,'MULTIPLE_PARENTS'):parents_of(nodes)
    def test_skin_identity_is_identity(self):
        p=np.array([[0,0,0],[1,0,0],[0,1,0]],dtype=np.float32)
        j=np.zeros((3,4),dtype=np.int32)
        w=np.tile([1.,0,0,0],(3,1)).astype(np.float32)
        np.testing.assert_allclose(skin_vertices(p,j,w,np.eye(4)[None,...]),p,atol=1e-6)
    def test_bad_skin_matrix_nan_rejected(self):
        p=np.ones((2,3),dtype=np.float32)
        j=np.zeros((2,4),dtype=np.int32)
        w=np.tile([1.,0,0,0],(2,1)).astype(np.float32)
        m=np.eye(4)[None,...];m[0,0,0]=float('nan')
        with self.assertRaisesRegex(ValueError,'SKIN_NUMERICAL_INVALID'):skin_vertices(p,j,w,m)
    def test_source_hash_fails(self):
        with self.assertRaises(ValueError):inspect(b'tamper','0'*64)

@unittest.skipUnless(CANDIDATE.exists(),'Exact source-bound GLB absent: no unpinned GHA model')
class TestActual72(unittest.TestCase):
    def test_real_source_cpu72(self):
        raw=CANDIDATE.read_bytes()
        r=inspect(raw,hashlib.sha256(raw).hexdigest())
        self.assertEqual(r['schema'],MOTION_SCHEMA)
        self.assertTrue(r['actual_72_frames_evaluated'])
        for actor in r['actors'].values():
            self.assertEqual(len(actor['frames']),72)
            self.assertTrue(actor['skin_rest_aligned_to_inverse_bind'])
            self.assertLess(actor['global_edge_stretch_p99_max_over_frames'],1.5)
            self.assertFalse(actor['motion_accepted'])

if __name__=='__main__':unittest.main()
