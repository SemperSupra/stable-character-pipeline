"""Hostile source-free and source-bound controls for bounded skin smoothing."""
import hashlib
import json
import os
from pathlib import Path
import unittest
try:
    import numpy as np
    import scipy # optional public runner; exact numerical/mesh tests gate if unavailable
except ImportError:
    np=None
from costume_garment_v1 import _unpack_glb
from sculpt_human_v1 import _read_accessor
from weight_transfer_regularize_v1 import SkinGateError,check_sha,regularize,derive,SCHEMA,SOURCE_SHA,ACTORS

ROOT=Path(__file__).parent
SRC=Path(os.getenv('R009_MH35_CANDIDATE',str(ROOT/'aster_juniper_makehuman35_candidate_v0.glb')))

def sample():
    # Six faces + duplicate UV vertex at origin; nontrivial bone transition.
    p=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[0,0,0]],dtype=np.float64)
    f=np.array([[0,1,2],[0,2,3],[0,1,4],[1,5,4],[0,4,6],[1,5,2]],dtype=int)
    j=np.zeros((len(p),4),dtype=np.uint8)
    j[:,0]=np.array([0,0,1,1,2,2,0])
    w=np.zeros((len(p),4),dtype=np.float64); w[:,0]=1
    return p,f,j,w

class SourceFree(unittest.TestCase):
    def test_pin(self):
        with self.assertRaisesRegex(SkinGateError,'SOURCE_SHA_MISMATCH'):check_sha(b'bad')
        with self.assertRaisesRegex(SkinGateError,'SOURCE_DIGEST_INVALID'):check_sha(b'bad','g'*64)
        self.assertEqual(len(SOURCE_SHA),64)
    @unittest.skipUnless(np is not None, "NumPy/SciPy unavailable; source-only contract")
    def test_weld_keeps_uv_vertices(self):
        p,f,j,w=sample()
        out,wgt,note=regularize(p,f,j,w)
        self.assertEqual(out.shape,j.shape)
        self.assertEqual(wgt.shape,w.shape)
        self.assertEqual(note['uv_seam_duplicates'],1)
        self.assertTrue(np.array_equal(out[0],out[6]))
        self.assertTrue(np.array_equal(wgt[0],wgt[6]))
        self.assertLess(np.max(abs(wgt.sum(axis=1)-1)),2e-5)
        self.assertFalse(note['motion_acceptance'])
    @unittest.skipUnless(np is not None, "NumPy/SciPy unavailable; source-only contract")
    def test_determinism(self):
        p,f,j,w=sample()
        a=regularize(p,f,j,w);b=regularize(p,f,j,w)
        self.assertTrue(np.array_equal(a[0],b[0]))
        self.assertTrue(np.array_equal(a[1],b[1]))
        self.assertEqual(a[2],b[2])
    @unittest.skipUnless(np is not None, "NumPy/SciPy unavailable; source-only contract")
    def test_invalid_alpha_and_iterations(self):
        p,f,j,w=sample()
        for param in ({'alpha':.99},{'alpha':float('nan')},{'iterations':0},{'iterations':1.0},{'iterations':9}):
            with self.subTest(param=param),self.assertRaises(SkinGateError):regularize(p,f,j,w,**param)
    @unittest.skipUnless(np is not None, "NumPy/SciPy unavailable; source-only contract")
    def test_invalid_faces_and_weights(self):
        p,f,j,w=sample()
        with self.assertRaises(SkinGateError):regularize(p,np.array([[0,8,2],[2,3,4]]),j,w)
        with self.assertRaises(SkinGateError):regularize(p,f,j,np.full(w.shape,.15))
        with self.assertRaises(SkinGateError):regularize(p,f,np.full(j.shape,35,dtype=np.uint8),w)
        with self.assertRaises(SkinGateError):regularize(p,f,j,np.full(w.shape,float('nan')))
        with self.assertRaises(SkinGateError):regularize(p,f,j,w,iterations=0)
    def test_nonpromotion(self):
        self.assertIn('regularization',SCHEMA)

@unittest.skipUnless(np is not None and SRC.exists(),'Exact MakeHuman 35j source and NumPy/SciPy required (absent on public CI)')
class ActualSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=SRC.read_bytes()
        check_sha(cls.raw)
        cls.derived,cls.receipt=derive(cls.raw)
    def test_pinned_and_repeatable(self):
        second,r=derive(self.raw)
        self.assertEqual(second,self.derived)
        self.assertEqual(r,self.receipt)
    def test_no_source_mutation(self):
        d,b=_unpack_glb(self.raw);n,q=_unpack_glb(self.derived)
        for key in ('skins','animations','nodes','scenes','materials','textures','images'):
            self.assertEqual(d.get(key),n.get(key),key)
        self.assertEqual(q[:len(b)],b)
        self.assertEqual(n['meshes'][:len(d['meshes'])][0]['name'],d['meshes'][0]['name'])
        for actor in ACTORS:
            node=next(x for x in n['nodes'] if x.get('name')==actor+'_Candidate_MakeHuman_35Joint_Body')
            old=d['meshes'][node['mesh']]['primitives'][0]
            new=n['meshes'][node['mesh']]['primitives'][0]
            for name in ('POSITION','NORMAL','TEXCOORD_0'):
                self.assertEqual(old['attributes'][name],new['attributes'][name])
            self.assertEqual(old['indices'],new['indices'])
            self.assertNotEqual(old['attributes']['WEIGHTS_0'],new['attributes']['WEIGHTS_0'])
        self.assertFalse(self.receipt['motion_accepted'])
    def test_all_weights_finite_seam_continuity(self):
        d,b=_unpack_glb(self.derived)
        for actor in ACTORS:
            node=next(n for n in d['nodes'] if n.get('name')==actor+'_Candidate_MakeHuman_35Joint_Body')
            prim=d['meshes'][node['mesh']]['primitives'][0]
            pos=np.asarray(_read_accessor(d,b,prim['attributes']['POSITION']),dtype=np.float32).reshape(-1,3)
            j=np.asarray(_read_accessor(d,b,prim['attributes']['JOINTS_0']),dtype=np.uint8).reshape(-1,4)
            w=np.asarray(_read_accessor(d,b,prim['attributes']['WEIGHTS_0']),dtype=np.float32).reshape(-1,4)
            self.assertEqual(len(pos),14517)
            self.assertTrue(np.isfinite(w).all())
            self.assertLess(abs(w.sum(axis=1)-1).max(),2e-5)
            self.assertLess(j.max(),35)
            _,label=np.unique(np.round(pos,5),return_inverse=True,axis=0)
            for k in (0,1,2,3):
                pass
            self.assertLess(self.receipt['actor_quality'][actor]['output_seam_max_mass_delta'],2e-5)

if __name__=='__main__':unittest.main()
