"""Sculpt v1 exact-source and hostile integrity tests, no Blender acceptance."""
import hashlib
import json
import os
import unittest
from pathlib import Path
from sculpt_human_v1 import sculpt,_unpack_glb,_read_accessor,_connected_components,SCHEMA,ACTORS,Builder

# External exact licensed / original GLB is NOT copied into public Git. Tests are
# non-promoting if local source corpus is absent; synthetic controls always run.
ROOT=Path(__file__).resolve().parents[1]/'wardrobe_batch'/'artifacts'
SOURCE=Path(os.environ.get('SCP_SCULPT_TEST_FIXTURE',str(ROOT/'r009_classic_adventurer_aster_juniper_35joint.glb')))

class SculptHostileSourceFreeTests(unittest.TestCase):
    def test_reject_wrong_source(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_SHA256_MISMATCH'):
            sculpt(b'not a source', 'a'*64)

    def test_loft_normalized_weights(self):
        b=Builder({'head':0})
        b.loft([(0.,0.1,0.,0.1,0.1),(0.,0.2,0.,0.1,0.1),
                (0.,0.3,0.,0.1,0.1)],radial=8)
        self.assertTrue(all(abs(sum(b.weight[i:i+4])-1)<1e-9
                            for i in range(0,len(b.weight),4)))

    def test_fail_unmapped_joint(self):
        b=Builder({'head':0})
        with self.assertRaisesRegex(ValueError,'RIG_ROLE_MISSING'):
            b.vert((0,0,0),(1,0,0),[('no-such-role',1.)])

@unittest.skipUnless(SOURCE.exists(), 'EXACT_SOURCE_CORPUS_NOT_LOCAL; technical tests skipped, not accepted')
class SculptSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=SOURCE.read_bytes()
        cls.sha=hashlib.sha256(cls.original).hexdigest()
        cls.derived,cls.record=sculpt(cls.original,cls.sha)
        cls.old,_=_unpack_glb(cls.original)
        cls.new,_=_unpack_glb(cls.derived)

    def test_distinct_body_surfaces(self):
        for name in ACTORS:
            r=self.record['actors'][name]
            self.assertEqual(r['replacement_groups']['replace_segmented_arm'],4)
            self.assertEqual(r['replacement_groups']['replace_segmented_leg'],4)
            self.assertGreater(r['removed_triangle_count'],11000)
            self.assertGreater(r['replacement_triangles'],6000)
            self.assertGreater(r['head_refine']['jaw_vertices'],50)
            self.assertEqual(len(r['eye_changes']),2)
            self.assertGreater(r['skirt_clearance_adjusted_vertices'],100)

    def test_structure_animation_skins_unmodified(self):
        self.assertEqual(self.old['skins'],self.new['skins'])
        self.assertEqual(self.old['animations'],self.new['animations'])
        self.assertEqual(len(self.old['meshes']),len(self.new['meshes']))
        self.assertEqual(len(self.old['nodes']),len(self.new['nodes']))
        self.assertEqual(len(self.old['materials']),len(self.new['materials']))
        self.assertEqual(self.new['extras']['source_original_sculpt_v1']['schema'],SCHEMA)
        self.assertFalse(self.record['photorealism_accepted'])
        self.assertFalse(self.record['release_approved'])

    def test_original_binary_preserved_prefix(self):
        _,before=_unpack_glb(self.original)
        _,after=_unpack_glb(self.derived)
        self.assertTrue(after.startswith(before))
        self.assertEqual(hashlib.sha256(self.original).hexdigest(),self.sha)

    def test_deterministic_replay(self):
        again,_=sculpt(self.original,self.sha)
        self.assertEqual(self.derived,again)

    def test_fail_closed_wrong_hash(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_SHA256_MISMATCH'):
            sculpt(self.original,'0'*64)

    def test_fail_closed_non_glb(self):
        raw=b'not a gltf'
        with self.assertRaises((ValueError,IndexError)):
            sculpt(raw,hashlib.sha256(raw).hexdigest())

    def test_skin_arrays_valid(self):
        doc,buf=_unpack_glb(self.derived)
        for name in ACTORS:
            idx=next(n['mesh'] for n in doc['nodes'] if n.get('name')==name+'_Wardrobe_body')
            prim=doc['meshes'][idx]['primitives'][-1]
            pos=_read_accessor(doc,buf,prim['attributes']['POSITION'])
            joints=_read_accessor(doc,buf,prim['attributes']['JOINTS_0'])
            weights=_read_accessor(doc,buf,prim['attributes']['WEIGHTS_0'])
            self.assertEqual(len(pos)*4//3,len(joints))
            self.assertEqual(len(weights),len(joints))
            self.assertTrue(all(0<=k<35 for k in joints))
            self.assertTrue(all(abs(sum(weights[i:i+4])-1)<.00001 for i in range(0,len(weights),4)))

    def test_source_scope_is_original_only(self):
        self.assertEqual(self.new['extras']['source_class'],'ORIGINAL_SELF_AUTHORED_SYNTHETIC')
        self.assertEqual(self.new['extras']['source_original_sculpt_v1']['source_sha256'],self.sha)
        self.assertEqual(self.new['extras']['costume_variant']['design'],'classic_adventurer')

if __name__=='__main__':unittest.main()
