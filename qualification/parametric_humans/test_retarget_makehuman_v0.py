"""Strict source-bound and source-free regression controls for CC0 35-joint candidate."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from costume_garment_v1 import _unpack_glb
from retarget_makehuman_v0 import (
  _require_input,source_to_target,RetargetError,derive,ACTORS,SCHEMA,
  SOURCE_OBJ_SHA256,SOURCE_GLB_SHA256,_smootherstep)

ROOT=Path(__file__).resolve().parent
SOURCE=Path(os.environ.get('R009_REPAIRED_CLASSIC_GLB', '/mnt/data/human_quality_batch/repaired/r009_classic_adventurer_sculpt_zeroarea_repaired_35joint.glb'))
OBJ=Path(os.environ.get('R009_MAKEHUMAN_BODY_OBJ','/mnt/data/MakeHuman_CC0_BodyOnly_SourcePinned_v1.obj'))
CANDIDATE=ROOT/'aster_juniper_makehuman35_candidate_v0.glb'

class TestHostile(unittest.TestCase):
    def test_smooth_gate_monotonic_bounded(self):
        z=[_smootherstep(i/20) for i in range(-3,24)]
        self.assertTrue(all(0<=v<=1 for v in z))
        self.assertTrue(all(a<=b for a,b in zip(z,z[1:])))
        self.assertEqual(_smootherstep(-1),0)
        self.assertEqual(_smootherstep(2),1)
    def test_pins_reject_wrong_hash(self):
        with self.assertRaisesRegex(RetargetError,'SOURCE_SHA_MISMATCH'):
            _require_input(b'one', '0'*64,'test')
        with self.assertRaisesRegex(RetargetError,'INVALID_SOURCE_PIN'):
            _require_input(b'one', 'bad','test')
    @unittest.skipUnless(__import__('importlib').util.find_spec('numpy') is not None, 'numpy unavailable')
    def test_unknown_actor(self):
        import numpy as np
        with self.assertRaisesRegex(RetargetError,'UNKNOWN_ACTOR'):
            source_to_target(np.zeros((600,3)), 'unknown')
    @unittest.skipUnless(__import__('importlib').util.find_spec('numpy') is not None, 'numpy unavailable')
    def test_invalid_vertices_and_coords(self):
        import numpy as np
        for x in (np.zeros((600,2)),np.full((600,3),float('nan')),np.full((600,3),101.)):
            with self.assertRaises(RetargetError):source_to_target(x,'JuniperOriginal')
    @unittest.skipUnless(__import__('importlib').util.find_spec('numpy') is not None, 'numpy unavailable')
    def test_continuous_pose_and_actor_variation(self):
        import numpy as np
        rs=np.random.default_rng(9).uniform([-2.,-8.,-1.],[2.,8.,3.],(700,3))
        a=source_to_target(rs,ACTORS[0]);j=source_to_target(rs,ACTORS[1])
        self.assertEqual(a.shape,(700,3));self.assertTrue(np.isfinite(a).all())
        self.assertGreater(float(np.linalg.norm(a-j)),.01)
        # Local perturbation has bounded positional response, including no cut seam.
        eps=np.zeros_like(rs);eps[:,0]=1e-5
        jp=source_to_target(rs+eps,ACTORS[1]);self.assertLess(float(np.max(np.linalg.norm(jp-j,axis=1))),.0002)
    def test_documented_conservative_controls(self):
        self.assertEqual(len(ACTORS),2)
        self.assertEqual(len(SOURCE_OBJ_SHA256),len(SOURCE_GLB_SHA256))
        self.assertEqual(SCHEMA,'scp.r009.makehuman35.retarget_candidate.v0')

@unittest.skipUnless(SOURCE.exists() and OBJ.exists() and CANDIDATE.exists(),
                     'Exact original source and MakeHuman CC0 files unavailable: no public source leak')
class TestActualSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=SOURCE.read_bytes();cls.obj=OBJ.read_bytes();cls.raw=CANDIDATE.read_bytes()
        if hashlib.sha256(cls.src).hexdigest()!=SOURCE_GLB_SHA256 or hashlib.sha256(cls.obj).hexdigest()!=SOURCE_OBJ_SHA256:
            raise ValueError('TEST_SOURCE_PIN_MISMATCH')
    def test_derivation_deterministic_and_pinned(self):
        out,rc=derive(self.src,self.obj)
        self.assertEqual(out,self.raw)
        self.assertEqual(rc['output_sha256'],hashlib.sha256(out).hexdigest())
        self.assertFalse(rc['rigging_accepted'])
        self.assertFalse(rc['garment_collision_accepted'])
    def test_source_geometry_and_animation_preserved(self):
        a,b=_unpack_glb(self.src);p,q=_unpack_glb(self.raw)
        self.assertEqual(p['animations'],a['animations'])
        self.assertEqual(p['skins'],a['skins'])
        self.assertEqual(p['meshes'][:len(a['meshes'])],a['meshes'])
        self.assertEqual(q[:len(b)],b)
        self.assertEqual(len(p['meshes']),len(a['meshes'])+2)
        self.assertEqual(len(p['nodes']),len(a['nodes'])+2)
        self.assertEqual(len(p['materials']),len(a['materials']))
        self.assertEqual(len(p['animations'][0]['channels']),len(a['animations'][0]['channels']))
        for actor in ACTORS:
            nodes={n['name']:n for n in p['nodes']}
            self.assertNotIn('mesh',nodes[actor+'_Wardrobe_body'])
            self.assertIn('mesh',nodes[actor+'_Candidate_MakeHuman_35Joint_Body'])
    def test_poses_and_joint_weights(self):
        from sculpt_human_v1 import _read_accessor
        import numpy as np
        d,b=_unpack_glb(self.raw)
        for ai,actor in enumerate(ACTORS):
            node=next(n for n in d['nodes'] if n['name']==actor+'_Candidate_MakeHuman_35Joint_Body')
            prim=d['meshes'][node['mesh']]['primitives'][0]
            w=np.asarray(_read_accessor(d,b,prim['attributes']['WEIGHTS_0'])).reshape(-1,4)
            j=np.asarray(_read_accessor(d,b,prim['attributes']['JOINTS_0'])).reshape(-1,4)
            self.assertEqual(len(w),14517)
            self.assertEqual(d['accessors'][prim['attributes']['TEXCOORD_0']]['count'],14517)
            self.assertLess(np.abs(w.sum(axis=1)-1).max(),1e-5)
            self.assertGreaterEqual(j.min(),0);self.assertLess(j.max(),35)

if __name__=='__main__':unittest.main()
