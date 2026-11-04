"""Self-authored hostile controls; they do not masquerade as genuine native receipts."""
import copy
import tempfile
import unittest
from pathlib import Path
from audit_receipt import ACTORS, BONES, FRAMES, audit, load_receipt

def fixture():
    samples=[]
    for i, f in enumerate(FRAMES):
        actors=[]
        for j, root in enumerate(ACTORS):
            x=(-2.9+2.1*i/5) if j==0 else (2.9-2.1*i/5)
            bone={k:0.0 for k in BONES}
            bone['Bip01 L Thigh']=[-.3,.2,.35,-.1,.1,-.3][i]
            actors.append({'root':root,'mean_x':x,'bounds_x':[x-.5,x+.5],
                           'evaluated_mesh_min_z':-.001,'animated_local_bones':bone})
        samples.append({'frame':f,'actors':actors})
    return {'schema':'scp.mit_rocketbox_native_walk.v1',
        'status':'NATIVE_SKINNED_WALK_SOURCE_ONLY_NOT_HUMAN_ACCEPTED',
        'source_rights':'MIT_with_notice','frame_count':72,'fps':12,
        'profile':'two_80_bone_actual_source_mesh_actors',
        'bone_basis_calibrated':False,'foot_contact':'UNKNOWN',
        'human_gait':'UNKNOWN','camera_visual_acceptance':'UNKNOWN',
        'product_accepted':False,'views':{'front':72,'oblique':72},'samples':samples}

class TestAudit(unittest.TestCase):
    def setUp(self):self.valid=fixture()
    def deny(self,mutate):
        d=copy.deepcopy(self.valid);mutate(d)
        with self.assertRaises(ValueError):audit(d)
    def test_positive_synthetic_shape_only(self):
        self.assertFalse(audit(self.valid)['product_accepted'])
    def test_forged_product(self):self.deny(lambda r:r.__setitem__('product_accepted',True))
    def test_forged_contact(self):self.deny(lambda r:r.__setitem__('foot_contact','PASS'))
    def test_forged_calibration(self):self.deny(lambda r:r.__setitem__('bone_basis_calibrated',True))
    def test_forged_human(self):self.deny(lambda r:r.__setitem__('human_gait','PASS'))
    def test_forged_source_rights(self):self.deny(lambda r:r.__setitem__('source_rights','CC0'))
    def test_missing_frame(self):self.deny(lambda r:r['samples'].pop())
    def test_wrong_frame_order(self):self.deny(lambda r:r['samples'][0].__setitem__('frame',1))
    def test_static_center(self):
        def change(r):
            for x in r['samples']:
                for a in x['actors']:a['mean_x']=0;a['bounds_x']=[-1,1]
        self.deny(change)
    def test_static_thigh(self):
        def change(r):
            for x in r['samples']:
                for a in x['actors']:a['animated_local_bones']['Bip01 L Thigh']=0
        self.deny(change)
    def test_nonfinite_min(self):
        self.deny(lambda r:r['samples'][0]['actors'][0].__setitem__('evaluated_mesh_min_z',float('nan')))
    def test_missing_bone(self):
        self.deny(lambda r:r['samples'][0]['actors'][0]['animated_local_bones'].pop('Bip01 L Thigh'))
    def test_duplicate_json_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'x.json';p.write_text('{"product_accepted":true,"product_accepted":false}')
            with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON_KEY'):load_receipt(p)
    def test_nan_json_constant(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'x.json';p.write_text('{"x":NaN}')
            with self.assertRaisesRegex(ValueError,'INVALID_JSON_CONSTANT'):load_receipt(p)
    def test_str_bool_confusion(self):
        self.deny(lambda r:r.__setitem__('frame_count',True))

if __name__=='__main__':unittest.main()
