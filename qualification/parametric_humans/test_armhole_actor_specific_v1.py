"""Optional owner-original source-bound 35-joint and actor-isolation controls."""
import os,unittest,hashlib,json
from pathlib import Path
from armhole_profile_contract_v1 import ACTORS
BASE_SHA256='a8b493eaba59c965713f4f70f0dccebebcfcc4f3d4ba9aa712d79915e1a05739'
class SourceBoundArmhole(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=os.environ.get('SCP_MH35_FITTED_SOURCE')
        if not path:raise unittest.SkipTest('Owner-only exact original research GLB not on public CI')
        cls.path=Path(path)
        if not cls.path.is_file():raise AssertionError('SOURCE_FILE_MISSING')
        cls.src=cls.path.read_bytes()
        if hashlib.sha256(cls.src).hexdigest()!=BASE_SHA256:
            raise AssertionError('SOURCE_SHA256_MISMATCH')
        import numpy # source-bound SciPy/NumPy pipeline intentionally unavailable on public CI
        from armhole_actor_specific_v1 import derive
        from costume_garment_v1 import _unpack_glb
        cls.derive=staticmethod(derive);cls.unpack=staticmethod(_unpack_glb)
    def test_deterministic_double_derive(self):
        m={ACTORS[0]:0.,ACTORS[1]:.01}
        first,one=self.derive(self.src,m);second,two=self.derive(self.src,m)
        self.assertEqual(first,second)
        self.assertEqual(one,two)
        self.assertEqual(one['derived_sha256'],'ae2b809ffa5cf5dfee0adf2f6b88b0a864e3588b95638de4c8b86e83a6e524af')
    def test_untouched_actor_and_all_rig_animation(self):
        raw,_=self.derive(self.src,{ACTORS[0]:0.,ACTORS[1]:.01})
        a,ba=self.unpack(self.src);b,bb=self.unpack(raw)
        self.assertEqual(ba,bb[:len(ba)])
        for k in ('skins','animations','scenes','scene'):
            self.assertEqual(a.get(k),b.get(k))
        aname=ACTORS[0]+'_Wardrobe_costume_top'
        nodea=next(n for n in a['nodes'] if n.get('name')==aname)
        nodeb=next(n for n in b['nodes'] if n.get('name')==aname)
        self.assertEqual(nodea,nodeb)
        self.assertEqual(a['meshes'][nodea['mesh']],b['meshes'][nodeb['mesh']])
        self.assertEqual([x.get('name') for x in a['nodes']],[x.get('name') for x in b['nodes']])
    def test_only_juniper_bodice_modified(self):
        raw,receipt=self.derive(self.src,{ACTORS[0]:0.,ACTORS[1]:.01})
        a,_=self.unpack(self.src);b,_=self.unpack(raw)
        self.assertEqual(len(b['meshes']),len(a['meshes'])+1)
        self.assertEqual(len(b['animations']),1)
        self.assertTrue(all(len(s['joints'])==35 for s in b['skins']))
        self.assertEqual(receipt['actors'][ACTORS[0]]['changed_vertices'],0)
        self.assertEqual(receipt['actors'][ACTORS[1]]['changed_vertices'],150)
        self.assertLess(receipt['actors'][ACTORS[1]]['max_edge_stretch'],1.15)
        self.assertFalse(receipt['release_approved'])
    def test_bad_sha_fail_closed(self):
        with self.assertRaises(ValueError):self.derive(self.src+b'\0',{ACTORS[0]:0.,ACTORS[1]:.01})
if __name__=='__main__':unittest.main()
