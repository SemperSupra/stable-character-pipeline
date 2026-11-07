"""Public-safe hostile tests for Lipschitz floor/continuity, not gait."""
import copy,hashlib,json,unittest
from root_y_lipschitz_envelope_v1 import build,envelope,EnvelopeError,SOURCE_SHA256,ACTORS
from root_y_envelope_dual_gate_v1 import evaluate,RECEIPT_SCHEMA,AFTER_SCHEMA

class EnvelopeDualGateTest(unittest.TestCase):
    def fixture(self):
        sole={'schema':'scp.r009.shoe_sole_correspondence_cpu72.v1','source_sha256':SOURCE_SHA256,'frames':72,'coordinate_up':'Y',
              'root_shift_applied':False,'native_blender_evaluated':False,'gait_accepted':False,'release_approved':False,
              'actors':{a:{'required_root_y_clearance_m':[.01]*72} for a in ACTORS}}
        raw=json.dumps(sole,sort_keys=True).encode()
        schedule=build(sole)
        receipt={'schema':RECEIPT_SCHEMA,'mode':'minimal_envelope','source_sha256':SOURCE_SHA256,
           'derived_sha256':'a'*64,'sole_witness_sha256':hashlib.sha256(raw).hexdigest(),
           'source_original_bin_prefix_preserved':True,'original_accessors_preserved':True,
           'non_root_animations_preserved':True,'rig_material_mesh_preserved':True,
           'root_ik_applied':False,'leg_ik_applied':False,'native_blender_evaluated':False,
           'physical_contact_accepted':False,'natural_gait_accepted':False,'release_approved':False,
           'schedule':schedule,'root_channels':[]}
        after={'schema':AFTER_SCHEMA,'source_sha256':'a'*64,'frames':72,'root_y_trial_executed':True,
            'foot_ik_applied':False,'root_ik_applied':False,'native_blender_evaluated':False,'gait_accepted':False,'release_approved':False,
            'per_side':{},'summary':{}}
        for i,actor in enumerate(ACTORS):
            receipt['root_channels'].append({'actor':actor,'root_node':i,'sampler':i,'original_accessor':20+i,
                'new_accessor':100+i,'min_lift_m':.0102,'max_lift_m':.0102,'max_step_m':0.})
            after['per_side'][actor]=[{'frame':f,'side':s,'min_y_m':.0002,
                   'vertices_below_minus_5mm':0,'vertices_within_10mm_floor':5} for f in range(72) for s in ('L','R')]
            after['summary'][actor]={'worst_shoe_y_m':.0002,'mean_stance_min_y_m':.0002,
               'frames_shoe_below_minus_5mm':0,'frames_both_feet_over_plus_10mm':0}
        return sole,receipt,after,raw
    def assert_bad(self,change):
        so,r,a,raw=self.fixture();change(so,r,a)
        with self.assertRaises(EnvelopeError):evaluate(so,r,a)
    def test_smooth_majorant_and_not_gait(self):
        so,r,a,raw=self.fixture();out=evaluate(so,r,a,raw)
        self.assertEqual(out['verdict'],'PASS_FLOOR_AND_CONTINUITY_PROXY_ONLY')
        self.assertFalse(out['natural_gait_accepted'])
    def test_nonconstant_envelope_proof(self):
        vals=[.010]*72;vals[20]=.013
        y=envelope(vals)
        self.assertGreaterEqual(y[20],.0132-1e-12)
        self.assertLessEqual(max(abs(y[i]-y[i-1]) for i in range(1,72)),.002+1e-12)
        self.assertLessEqual(max(abs(y[i+1]-2*y[i]+y[i-1]) for i in range(1,71)),.004+1e-12)
    def test_cyclic_wrap_derivative(self):
        vals=[.007]*72; vals[-1]=.015
        y=envelope(vals)
        self.assertLessEqual(abs(y[0]-y[-1]),.002+1e-12)
        self.assertLessEqual(abs(y[1]-2*y[0]+y[-1]),.004+1e-12)
    def test_constant_upper_bound_research_foil(self):
        so,r,a,raw=self.fixture();d=build(so,'constant_upper_bound')
        self.assertEqual(len(set(d['actors']['AsterOriginal']['proposed_lift_m'])),1)
    def test_floor_violation_in_actual_witness(self):
        self.assert_bad(lambda so,r,a:a['per_side']['AsterOriginal'][0].update(min_y_m=-.02,vertices_below_minus_5mm=1))
    def test_duplicate_frame(self):
        self.assert_bad(lambda so,r,a:a['per_side']['JuniperOriginal'].__setitem__(1,a['per_side']['JuniperOriginal'][0]))
    def test_mismatched_sole_source(self):self.assert_bad(lambda so,r,a:so.update(source_sha256='0'*64))
    def test_mismatched_derivative(self):self.assert_bad(lambda so,r,a:a.update(source_sha256='0'*64))
    def test_forged_schedule(self):self.assert_bad(lambda so,r,a:r['schedule']['actors']['AsterOriginal']['proposed_lift_m'].__setitem__(0,.012))
    def test_forged_gait(self):self.assert_bad(lambda so,r,a:r.update(natural_gait_accepted=True))
    def test_fake_blender(self):self.assert_bad(lambda so,r,a:a.update(native_blender_evaluated=True))
    def test_fake_original_prefix(self):self.assert_bad(lambda so,r,a:r.update(source_original_bin_prefix_preserved=False))
    def test_overwrite_accessor(self):self.assert_bad(lambda so,r,a:r['root_channels'][0].update(new_accessor=20))
    def test_false_producer_bounds(self):self.assert_bad(lambda so,r,a:r['root_channels'][0].update(max_step_m=.02))
    def test_missing_frame(self):self.assert_bad(lambda so,r,a:a['per_side']['JuniperOriginal'].pop())
    def test_forged_summary(self):self.assert_bad(lambda so,r,a:a['summary']['JuniperOriginal'].update(worst_shoe_y_m=0.))
    def test_negative_required_height(self):self.assert_bad(lambda so,r,a:so['actors']['AsterOriginal']['required_root_y_clearance_m'].__setitem__(2,-.2))
    def test_nonfinite_required(self):self.assert_bad(lambda so,r,a:so['actors']['JuniperOriginal']['required_root_y_clearance_m'].__setitem__(3,float('nan')))
    def test_missing_source_bin_flag(self):self.assert_bad(lambda so,r,a:r.pop('source_original_bin_prefix_preserved'))
    def test_wrong_coordinate_axis(self):self.assert_bad(lambda so,r,a:so.update(coordinate_up='Z'))
    def test_unsafe_slope(self):
        with self.assertRaises(EnvelopeError):envelope([.01]*72,slope=.004)
    def test_bad_margin(self):
        with self.assertRaises(EnvelopeError):envelope([.01]*72,margin=0.)
    def test_wrong_actor(self):self.assert_bad(lambda so,r,a:so['actors'].pop('JuniperOriginal'))
if __name__=='__main__':unittest.main()
