"""Adversarial source-only and actual original 35-joint weight-transfer trials."""
import hashlib,os,unittest
from pathlib import Path
import numpy as np
from skirt_yoke_weight_trial_v1 import make_weights,derive,WeightTrialError,SOURCE_SHA256

class WeightMappingTests(unittest.TestCase):
    def setUp(self):
        self.points=np.tile(np.array([[0.,.69,0.],[.12,.73,0.],[-.12,.76,0.],[0.,1.04,0.]]),(30,1))
    def test_normalized_finite(self):
        w=make_weights(self.points,.45,.50)
        self.assertEqual(w.shape,(120,4))
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertLess(float(np.max(abs(w.sum(axis=1)-1))),2e-7)
    def test_waist_keeps_spine(self):
        w=make_weights(self.points,.45,.50)
        self.assertTrue(np.array_equal(w[3],[1.,0.,0.,0.]))
    def test_lower_hem_gets_anatomical_hip(self):
        w=make_weights(self.points,.45,.50)
        self.assertGreater(float(w[1,3]),float(w[1,2]))
        self.assertGreater(float(w[2,2]),float(w[2,3]))
    def test_no_horizontal_seam_discontinuity(self):
        p=np.array([[x,.72,0.] for x in np.linspace(-.2,.2,301)])
        w=make_weights(p,.45,.5)
        self.assertLess(float(np.max(abs(np.diff(w[:,2])))),.005)
    def test_malformed_parameters_fail(self):
        for x,y in [(-.1,.2),(1.,.2),(.3,-.1),(.3,.85),(float('nan'),.3),(True,.2)]:
            with self.subTest(x=x,y=y),self.assertRaises(WeightTrialError):make_weights(self.points,x,y)
    def test_malformed_vertex_fail(self):
        with self.assertRaises(WeightTrialError):make_weights([[float('nan'),.7,0]]*120,.3,.2)
    def test_source_integrity(self):
        with self.assertRaises(WeightTrialError):derive(b'corrupted','JuniperOriginal',.3,.2)

class ActualSkirtTrial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=os.environ.get('SCP_R009_JUNIPER_ARMHOLE_GLB')
        if not path:raise unittest.SkipTest('Exact source not present in public CI')
        cls.raw=Path(path).read_bytes()
        if hashlib.sha256(cls.raw).hexdigest()!=SOURCE_SHA256:raise AssertionError('SOURCE_HASH_NOT_ADMITTED')
    def test_deterministic_preserve_other_actor(self):
        from costume_garment_v1 import _unpack_glb
        a,rec=derive(self.raw,'JuniperOriginal',.35,.3)
        b,rec2=derive(self.raw,'JuniperOriginal',.35,.3)
        self.assertEqual(a,b);self.assertEqual(rec,rec2)
        before,bb=_unpack_glb(self.raw);after,ab=_unpack_glb(a)
        self.assertEqual(before['skins'],after['skins'])
        self.assertEqual(before['animations'],after['animations'])
        self.assertEqual(before['scenes'],after['scenes'])
        self.assertEqual(before['nodes'][:len(before['nodes'])][0],after['nodes'][0])
        self.assertEqual(before['nodes'][0]['name'],after['nodes'][0]['name'])
        self.assertEqual(bb,ab[:len(bb)])
        self.assertEqual(len(after['meshes']),len(before['meshes'])+1)
        self.assertEqual(rec['max_lower_weight'],.35)
        self.assertFalse(rec['garment_fit_accepted'])

if __name__=='__main__':unittest.main()
