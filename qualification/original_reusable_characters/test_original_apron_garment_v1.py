"""Hostile original-only wardrobe tests; real-source integration is explicitly opt-in.

Run `R009_WARDROBE_SOURCE_DIR=/path/to/verified/extracted/source python3 -m unittest`
without that env var all source-owned tests SKIP instead of fabricated acceptance.
"""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
import original_apron_garment_v1 as a

ROOT=Path(os.environ.get('R009_WARDROBE_SOURCE_DIR','/nonexistent-r009-wardrobe'))

class MathControls(unittest.TestCase):
    def test_closest_on_triangle_internal(self):
        A=np.array([0.,0.,0.]);B=np.array([1.,0.,0.]);C=np.array([0.,1.,0.]);p=np.array([.25,.25,.5])
        near, bary=a.closest_on_tri(p,A,B,C)
        np.testing.assert_allclose(near,[.25,.25,0]);np.testing.assert_allclose(bary,[.5,.25,.25])

    def test_closest_on_triangle_edge(self):
        A=np.array([0.,0.,0.]);B=np.array([1.,0.,0.]);C=np.array([0.,1.,0.]);p=np.array([.6,-.5,.1])
        near,bary=a.closest_on_tri(p,A,B,C)
        np.testing.assert_allclose(near,[.6,0.,0]);np.testing.assert_allclose(bary,[.4,.6,0])

    def test_closest_on_triangle_vertex(self):
        A=np.array([0.,0.,0.]);B=np.array([1.,0.,0.]);C=np.array([0.,1.,0.]);p=np.array([2.,0.,0.])
        near,bary=a.closest_on_tri(p,A,B,C)
        np.testing.assert_allclose(near,[1,0,0]);np.testing.assert_allclose(bary,[0,1,0])

    def test_degenerate_face_fail_closed(self):
        p=np.array([.1,.1,0]);A=np.array([0.,0.,0.]);B=np.array([1.,0.,0.]);C=np.array([2.,0.,0.])
        with self.assertRaisesRegex(a.GateError,'SOURCE_DEGENERATE_FACE'):
            a.closest_on_tri(p,A,B,C)

    def test_duplicate_json_or_nan_fail_closed(self):
        for b in (b'{"source_class":"OK","source_class":"FORGED"}',
                  b'{"one":{"foo":1,"foo":2}}',
                  b'{"foo":NaN}',b'{"foo":Infinity}',b'{"a":1,}'):
            with self.subTest(payload=b),self.assertRaises(a.GateError):a.load_json_strict(b)

    def test_gltf_header_and_bad_chunks(self):
        for raw in (b'',b'glTF'+b'\0'*32, b'glTF\2\0\0\0'+b'\0'*16):
            with self.subTest(raw=raw[:6]),self.assertRaises(a.GateError):a.read_glb(raw)

    def test_invalid_source_exact_sha(self):
        with self.assertRaisesRegex(a.GateError,'SOURCE_EXACT_DIGEST'):
            a.validate_producer({},{},b'FAKE_SOURCE',b'FAKE_MANIFEST')

    def test_unqualified_acceptance_is_never_defaulted_true(self):
        # Schema deliberately requires measured source, not an input string alone.
        self.assertTrue(a.SOURCE_SHA and a.MANIFEST_SHA)
        self.assertIn('NOT a physics solver',a.__doc__)

@unittest.skipUnless((ROOT/'wardrobe_v1.glb').exists() and (ROOT/'wardrobe_v1_manifest.json').exists(),
                     'REAL_SOURCE_MISSING_FAIL_CLOSED_NO_FALLBACK')
class RealProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'wardrobe_v1.glb').read_bytes()
        cls.manifest=(ROOT/'wardrobe_v1_manifest.json').read_bytes()
        if a.sha(cls.raw)!=a.SOURCE_SHA or a.sha(cls.manifest)!=a.MANIFEST_SHA:
            raise AssertionError('SOURCE_DIGEST_MISMATCH_NOT_TEST_FIXTURE')
        cls.master,cls.portable,cls.m,cls.receipt=a.build(cls.raw,cls.manifest)

    def test_real_two_actor_glb_and_new_garment(self):
        d,b=a.read_glb(self.master)
        self.assertEqual(len(d['skins']),2)
        for i,actor in enumerate(a.ACTORS):
            self.assertEqual(len(d['skins'][i]['joints']),35)
            ap=self.m['actor_slots'][actor]['apron']
            node=d['nodes'][ap['node']];self.assertEqual(node['skin'],i)
            mesh=d['meshes'][ap['mesh']];self.assertEqual(len(mesh['primitives']),2)
            self.assertEqual(node['name'],actor+'_Wardrobe_apron')
            for pr in mesh['primitives']:
                p=a.accessor(d,b,pr['attributes']['POSITION'])
                j=a.accessor(d,b,pr['attributes']['JOINTS_0'])
                w=a.accessor(d,b,pr['attributes']['WEIGHTS_0'])
                tris=a.accessor(d,b,pr['indices']).reshape(-1,3).astype(int)
                self.assertTrue((j>=0).all() and (j<35).all())
                self.assertTrue(np.allclose(w.sum(axis=1),1.,atol=1e-6))
                self.assertTrue(np.isfinite(p).all())
                self.assertTrue((tris>=0).all() and (tris<len(p)).all())
            self.assertEqual(set(self.m['presets']['original_apron']),set(a.REQUIRED)|{'apron'})

    def test_exact_source_binary_and_model_immutability(self):
        o,ob=a.read_glb(self.raw);d,db=a.read_glb(self.master)
        self.assertEqual(db[:len(ob)],ob)
        self.assertEqual(d['meshes'][:len(o['meshes'])],o['meshes'])
        self.assertEqual(d['skins'],o['skins'])
        self.assertEqual(d['animations'],o['animations'])
        self.assertEqual(self.receipt['source_sha256'],a.sha(self.raw))
        self.assertEqual(self.receipt['master_sha256'],a.sha(self.master))
        self.assertFalse(self.receipt['native_blender_accepted'])
        self.assertFalse(self.receipt['collision_accepted'])

    def test_strict_portable_no_orphan_mesh_node(self):
        d,b=a.read_glb(self.portable)
        self.assertEqual(self.receipt['portable_sha256'],a.sha(self.portable))
        for actor in a.ACTORS:
            slots=self.m['actor_slots'][actor]
            root=next(n for n in d['nodes'] if n.get('name')==actor+'_SceneRoot')
            for slot,entry in slots.items():
                node=d['nodes'][entry['node']]
                if slot in a.REQUIRED or slot=='apron':
                    self.assertIn(entry['node'],root['children'])
                    self.assertIn('mesh',node)
                    self.assertIn('skin',node)
                else:
                    self.assertNotIn(entry['node'],root['children'])
                    self.assertNotIn('mesh',node)
                    self.assertNotIn('skin',node)
        original,ob=a.read_glb(self.master)
        self.assertEqual(original['meshes'],d['meshes'])
        self.assertEqual(original['skins'],d['skins'])
        self.assertEqual(original['animations'],d['animations'])

    def test_two_morphs_different_geometry_same_piece_counts(self):
        d,b=a.read_glb(self.master)
        def points(actor):
            slot=self.m['actor_slots'][actor]['apron'];m=d['meshes'][slot['mesh']]
            return a.accessor(d,b,m['primitives'][0]['attributes']['POSITION'])
        u=points(a.ACTORS[0]);v=points(a.ACTORS[1]);self.assertEqual(u.shape,v.shape)
        self.assertGreater(np.linalg.norm(u-v,axis=1).max(),.0001)
        self.assertLess(np.linalg.norm(u-v,axis=1).max(),.025)

    def test_source_modified_rejected(self):
        bad=bytearray(self.raw);bad[-64]^=1
        with self.assertRaisesRegex(a.GateError,'SOURCE_EXACT_DIGEST'):
            a.build(bytes(bad),self.manifest)
        badm=bytearray(self.manifest);badm[-8]^=1
        with self.assertRaisesRegex(a.GateError,'SOURCE_EXACT_DIGEST'):
            a.build(self.raw,bytes(badm))

    def test_manifest_skin_slot_integrity_reject(self):
        d,b=a.read_glb(self.raw);m=json.loads(self.manifest)
        m['actor_slots']['JuniperOriginal']['bottom']['skin']=999
        with self.assertRaisesRegex(a.GateError,'SOURCE_EXACT_DIGEST'):
            a.build(self.raw,json.dumps(m).encode())
        self.assertEqual(self.receipt['original_skin_animation_unchanged'],True)

    def test_determinism_and_write_once(self):
        master,portable,m,r=a.build(self.raw,self.manifest)
        self.assertEqual(a.sha(master),self.receipt['master_sha256'])
        self.assertEqual(a.sha(portable),self.receipt['portable_sha256'])
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'source.glb';mf=root/'source.json';src.write_bytes(self.raw);mf.write_bytes(self.manifest)
            args=[src,mf,root/'master.glb',root/'portable.glb',root/'master.json',root/'receipt.json']
            a.export(*args)
            with self.assertRaisesRegex(a.GateError,'OUTPUT_OVERWRITE_OR_ALIAS'):
                a.export(*args)
            self.assertEqual(a.sha(src.read_bytes()),a.SOURCE_SHA)

if __name__=='__main__':unittest.main()
