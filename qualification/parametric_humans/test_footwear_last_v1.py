"""R009 foot-last source-only and real-input hostile qualification controls."""
import hashlib,json,os,tempfile,unittest
from pathlib import Path
import numpy as np
from footwear_last_v1 import (ACTORS,SCHEMA,SOURCE_SHA256,LastError,last_geometry,derive)
from costume_garment_v1 import _unpack_glb
from sculpt_human_v1 import _read_accessor

SOURCE=Path(os.environ.get('R009_SHOE_SOURCE','/nonexistent'))
class FootwearLastTest(unittest.TestCase):
    def test_sha_fails_closed(self):
        with self.assertRaisesRegex(LastError,'SOURCE_SHA_MISMATCH'):
            derive(b'not-original')
    def test_side_fails_closed(self):
        with self.assertRaisesRegex(LastError,'SIDE_REQUIRED'):
            last_geometry(None,0)
    def test_ease_fails_closed(self):
        with self.assertRaisesRegex(LastError,'INVALID_EASE'):
            last_geometry(None,-1,ease=-.3)
    def test_radial_fails_closed(self):
        with self.assertRaisesRegex(LastError,'INVALID_RADIAL'):
            last_geometry(None,-1,radial=15)
    @unittest.skipUnless(SOURCE.is_file(),'EXACT_ORIGINAL_SOURCE_NOT_ATTACHED')
    def test_exact_source_and_skin_integrity(self):
        raw=SOURCE.read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),SOURCE_SHA256)
        out,receipt=derive(raw)
        self.assertEqual(receipt['schema'],SCHEMA)
        self.assertFalse(receipt['release_approved'])
        self.assertTrue(receipt['source_binary_prefix_preserved'])
        before,bin_before=_unpack_glb(raw)
        after,bin_after=_unpack_glb(out)
        self.assertEqual(bin_after[:len(bin_before)],bin_before)
        for name in ('animations','skins','materials','scenes','scene'):
            self.assertEqual(before[name],after[name])
        for who in ACTORS:
            node=next(x for x in after['nodes'] if x.get('name')==who+'_Wardrobe_footwear')
            old=next(x for x in before['nodes'] if x.get('name')==who+'_Wardrobe_footwear')
            self.assertEqual(node['extras']['pre_fit_mesh_id'],old['mesh'])
            self.assertNotEqual(node['mesh'],old['mesh'])
            self.assertEqual(after['skins'][node['skin']],before['skins'][old['skin']])
            mesh=after['meshes'][node['mesh']]['primitives'][0]
            positions=np.array(_read_accessor(after,bin_after,mesh['attributes']['POSITION']),float).reshape(-1,3)
            triangle=np.array(_read_accessor(after,bin_after,mesh['indices']),int).reshape(-1,3)
            weights=np.array(_read_accessor(after,bin_after,mesh['attributes']['WEIGHTS_0']),float).reshape(-1,4)
            joints=np.array(_read_accessor(after,bin_after,mesh['attributes']['JOINTS_0']),int).reshape(-1,4)
            self.assertEqual(len(positions),sum(x['vertices'] for x in receipt['actors'][who]))
            self.assertGreater(len(triangle),2000)
            self.assertTrue(np.isfinite(positions).all())
            self.assertTrue(np.allclose(weights.sum(axis=1),1,atol=1e-5))
            self.assertLess(int(joints.max()),35)
            a=np.cross(positions[triangle[:,1]]-positions[triangle[:,0]],
                       positions[triangle[:,2]]-positions[triangle[:,0]])
            self.assertTrue((np.linalg.norm(a,axis=1)>1e-8).all())
            self.assertTrue(all(x['negative_gt_5mm_fraction']==0 for x in receipt['actors'][who]))
        # Deterministic bytes, not just matching counts/JSON receipts.
        again,_=derive(raw)
        self.assertEqual(out,again)

if __name__=='__main__':unittest.main()
