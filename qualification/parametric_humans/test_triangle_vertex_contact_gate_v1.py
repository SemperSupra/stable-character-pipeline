"""Stdlib adversarial tests for coupled triangle and vertex witnesses."""
import copy,hashlib,json,unittest
from pathlib import Path
from triangle_vertex_contact_gate_v1 import SCHEMA,BVH,SIGNED,GateError,validate,compare

def fixture(sha='a'*64,tri=3,frac=0.0):
    fr=['rest',0,1]
    bvh={'schema':BVH,'source_sha256':sha,'frames':fr,'frame_count':3,
         'native_blender_evaluated':False,'cloth_physics_qualified':False,
         'no_triangle_crossing_proven':False,'wearable_fit_accepted':False,
         'release_approved':False,'actors':{}}
    signed={'schema':SIGNED,'source_sha256':sha,'witness_frames':fr,
         'native_blender_evaluated':False,'cloth_fitting_accepted':False,
         'release_approved':False,'actors':{}}
    for actor in ('AsterOriginal','JuniperOriginal'):
        bvh['actors'][actor]={'slots':{}}
        signed['actors'][actor]={'slots':{}}
        for slot in ('costume_top','costume_bottom','costume_trim','footwear'):
            bvh['actors'][actor]['slots'][slot]=[{'frame':f,'triangle_contact_pairs':tri} for f in fr]
            signed['actors'][actor]['slots'][slot]=[{'frame':f,'negative_gt_5mm_fraction':frac,'sign_calibrated':True} for f in fr]
    return bvh,signed

class DualWitness(unittest.TestCase):
    def test_positive_valid(self):
        a,b=fixture();self.assertEqual(len(validate(a,b)),2)
    def test_true_improvement_relative_only(self):
        a,b=fixture();c,d=fixture('b'*64,tri=2)
        r=compare(a,b,c,d)
        self.assertEqual(r['verdict'],'PASS_RELATIVE_ONLY')
        self.assertFalse(r['wearable_fit_accepted'])
        self.assertFalse(r['native_blender_evaluated'])
    def test_vertex_regression_rejects_crossing_gain(self):
        a,b=fixture();c,d=fixture('b'*64,tri=0,frac=.01)
        self.assertEqual(compare(a,b,c,d)['verdict'],'RED_REGRESSION')
    def test_triangle_regression_rejects_vertex_gain(self):
        a,b=fixture(frac=.1);c,d=fixture('b'*64,tri=4,frac=0)
        self.assertEqual(compare(a,b,c,d)['verdict'],'RED_REGRESSION')
    def test_noop_held(self):
        a,b=fixture();c,d=fixture('b'*64)
        self.assertEqual(compare(a,b,c,d)['verdict'],'HOLD_NO_GAIN')
    def test_identical_sha_rejected(self):
        a,b=fixture()
        with self.assertRaisesRegex(GateError,'IDENTICAL_SOURCE'):
            compare(a,b,*fixture())
    def test_mixed_sources_rejected(self):
        a,b=fixture();b['source_sha256']='b'*64
        with self.assertRaisesRegex(GateError,'MISMATCHED'):
            validate(a,b)
    def test_clocks_rejected(self):
        a,b=fixture();b['witness_frames']=['rest',1,2]
        with self.assertRaisesRegex(GateError,'UNPAIRED'):
            validate(a,b)
    def test_malformed_qualifications_rejected(self):
        a,b=fixture();a['no_triangle_crossing_proven']=True
        with self.assertRaisesRegex(GateError,'FALSE_BVH_APPROVAL'):
            validate(a,b)
    def test_negative_and_nan_rejected(self):
        for count in (-1,2.5):
            a,b=fixture();a['actors']['AsterOriginal']['slots']['footwear'][0]['triangle_contact_pairs']=count
            with self.assertRaises(GateError):validate(a,b)
        a,b=fixture();b['actors']['JuniperOriginal']['slots']['footwear'][1]['negative_gt_5mm_fraction']=float('nan')
        with self.assertRaises(GateError):validate(a,b)
    def test_sign_abstention_rejected(self):
        a,b=fixture();b['actors']['AsterOriginal']['slots']['footwear'][0]['sign_calibrated']=False
        with self.assertRaisesRegex(GateError,'UNQUALIFIED_SIGNED_SAMPLE'):
            validate(a,b)
    def test_actual_data_reject_both_trials(self):
        root=Path(__file__).resolve().parent
        base=root/'footwear_cross_section_opening_v1'
        if not (root/(base.name+'.bvh9.json')).exists():self.skipTest('owner-local source receipt only')
        p=json.loads((root/(base.name+'.bvh9.json')).read_text())
        s=json.loads((root/(base.name+'.glb.signed9.json')).read_text())
        for stem in ('costume_bottom_radial_08_trial','costume_bottom_radial_14_trial'):
            q=json.loads((root/(stem+'.bvh9.json')).read_text())
            t=json.loads((root/(stem+'.glb.signed9.json')).read_text())
            result=compare(p,s,q,t)
            self.assertEqual(result['verdict'],'RED_REGRESSION')
            self.assertGreater(len(result['regressions']),0)

if __name__=='__main__':unittest.main()
