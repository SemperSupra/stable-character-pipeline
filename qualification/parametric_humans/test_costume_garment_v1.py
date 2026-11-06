"""No external data: adversarial source, garment and GLB contract tests."""
import hashlib
import json
import math
import struct
import tempfile
import unittest
from pathlib import Path
import costume_garment_v1 as c

class OutfitContractTests(unittest.TestCase):
    def test_four_original_designs_two_actors(self):
        self.assertEqual(len(c.STYLES),4)
        for a in c.ACTORS:
            for style in c.STYLES:
                shapes=c.design_geometry(a,style)
                self.assertTrue({'top','bottom','trim'}<=set(shapes))
                if style=='high_collar_adventurer':self.assertIn('collar',shapes)
                for geo in shapes.values():
                    self.assertTrue(len(geo['indices'])>0)
                    self.assertTrue(all(math.isfinite(x) for x in geo['POSITION']))
                    self.assertEqual(len(geo['POSITION'])//3,len(geo['JOINTS_0'])//4)
                    self.assertEqual(len(geo['POSITION'])//3,len(geo['WEIGHTS_0'])//4)
                    for i in range(0,len(geo['WEIGHTS_0']),4):
                        self.assertAlmostEqual(sum(geo['WEIGHTS_0'][i:i+4]),1.)

    def test_source_rejected_before_decode(self):
        for raw in (b'',b'not a glb',b'glTF'+b'\x00'*100):
            with self.assertRaisesRegex(ValueError,'SOURCE_SHA256'):
                c.variant(raw,'casual')

    def test_bad_design_and_fits(self):
        with self.assertRaisesRegex(ValueError,'UNKNOWN_DESIGN'):
            c.design_geometry('AsterOriginal','leo')
        with self.assertRaisesRegex(ValueError,'UNKNOWN_DESIGN_OR_ACTOR'):
            c.design_geometry('random','casual')
        for field,bad in [('chest_scale',float('nan')),('waist_scale',.1),('hip_scale',True),('ease_m',0)]:
            fit=dict(c.DEFAULT_FIT);fit[field]=bad
            with self.assertRaises(ValueError):c.design_geometry('JuniperOriginal','casual',fit)
        with self.assertRaises(ValueError):c.validate_fit({'ease_m':.01})

    def test_ring_winding_and_invalid(self):
        for r in ([(1,.1,.1),(1,.2,.2),(1.2,.2,.2)],[(1,.1,.1),(2,.1,.1)],[(1,.1,.1),(2,float('nan'),.1),(3,.1,.1)]):
            with self.assertRaises(ValueError):c._ring_mesh(r)
        ring=c._ring_mesh([(.8,.2,.1),(.9,.2,.1),(1.,.2,.1)])
        for x in ring['indices']:self.assertLess(x,len(ring['POSITION'])//3)

    def test_packing_glb_min_max_and_invalid_components(self):
        d={'buffers':[{'byteLength':0}],'bufferViews':[],'accessors':[]}
        data=bytearray()
        self.assertEqual(c._accessor(d,data,[.1,.2,.3,1.,2.,3.],comp_type=5126,shape='VEC3',count=2,add_bounds=True),0)
        self.assertEqual(d['accessors'][0]['min'],[.1,.2,.3])
        self.assertEqual(d['accessors'][0]['max'],[1.,2.,3.])
        with self.assertRaises(ValueError):c._accessor(d,data,[float('nan')]*3,comp_type=5126,shape='VEC3',count=1)
        with self.assertRaises(ValueError):c._accessor(d,data,[256]*4,comp_type=5121,shape='VEC4',count=1)
        out=c._pack_glb(d,data)
        decoded,buf=c._unpack_glb(out)
        self.assertEqual(decoded['accessors'][0]['count'],2)
        self.assertGreaterEqual(len(buf),len(data))
        with self.assertRaises(ValueError):c._unpack_glb(out[:-1])

    def test_deterministic_source_bound_real_35joint_when_supplied(self):
        # Optional local genuine source witness; CI never downloads a binary.
        import os
        path=os.environ.get('SCP_R009_WARDROBE_MASTER')
        if not path:
            self.skipTest('NO_LOCAL_ORIGINAL_MASTER_GLB')
        src=Path(path).read_bytes()
        self.assertEqual(hashlib.sha256(src).hexdigest(),c.SOURCE_SHA256)
        for style in c.STYLES:
            b=c.variant(src,style)
            self.assertEqual(b,c.variant(src,style))
            d,_=c._unpack_glb(b)
            self.assertEqual(len(d['skins']),2)
            self.assertEqual(len(d['animations']),1)
            self.assertEqual([len(s['joints']) for s in d['skins']],[35,35])
            self.assertEqual(d['extras']['costume_variant']['design'],style)
            for actor in c.ACTORS:
                byname={n['name']:n for n in d['nodes'] if 'name' in n}
                root=byname[actor+'_SceneRoot']
                names=[d['nodes'][i]['name'] for i in root['children']]
                self.assertIn(actor+'_Wardrobe_body',names)
                self.assertIn(actor+'_Wardrobe_costume_top',names)
                self.assertIn(actor+'_Wardrobe_costume_bottom',names)
                self.assertNotIn(actor+'_Wardrobe_top',names)
                self.assertNotIn(actor+'_Wardrobe_bottom',names)

if __name__=='__main__':unittest.main()
