"""Public-safe fail-closed tests: floor fixes must not conceal height jitter."""
from __future__ import annotations
import copy
import hashlib
import json
import unittest
from root_y_trial_gate_v1 import evaluate, RootTrialGateError, SCHEMA, AFTER_SCHEMA, ORIGINAL_SHA256

class RootHeightContract(unittest.TestCase):
    def fixture(self):
        receipt={'schema':SCHEMA,'source_sha256':ORIGINAL_SHA256,
                 'derived_sha256':'a'*64,'sole_witness_sha256':'0'*64,
                 'root_channels':[],
                 'source_binary_prefix_equal':True,'all_original_accessors_preserved':True,
                 'root_y_only':True,'source_geometry_unchanged':True,'source_skin_unchanged':True,
                 'source_animation_non_root_unchanged':True,'root_y_corrected_proxy_only':True,
                 'root_ik_applied':False,'foot_lock_accepted':False,'native_blender_evaluated':False,
                 'gait_accepted':False,'release_approved':False}
        after={'schema':AFTER_SCHEMA,'source_sha256':'a'*64,'frames':72,'per_side':{},'summary':{},
               'root_y_trial_executed':True,'foot_ik_applied':False,'root_ik_applied':False,
               'native_blender_evaluated':False,'gait_accepted':False,'release_approved':False}
        sole={'source_sha256':ORIGINAL_SHA256,'frames':72,'actors':{}}
        for i,actor in enumerate(('AsterOriginal','JuniperOriginal')):
            lift=[.01]*72
            sole['actors'][actor]={'required_root_y_clearance_m':lift}
            receipt['root_channels'].append({'actor':actor,'root_node':i,'original_accessor':20+i,
                                             'new_accessor':30+i,'min_lift_m':.01,'max_lift_m':.01,
                                             'max_step_m':0.})
            after['per_side'][actor]=[{'frame':f,'side':s,'min_y_m':0.,
                                      'vertices_below_minus_5mm':0,'vertices_within_10mm_floor':15}
                                      for f in range(72) for s in ('L','R')]
            after['summary'][actor]={'worst_shoe_y_m':0.,'mean_stance_min_y_m':0.,
                                      'frames_shoe_below_minus_5mm':0,'frames_both_feet_over_plus_10mm':0}
        return receipt,after,sole
    def bad(self,mutator):
        a,b,c=self.fixture();mutator(a,b,c)
        with self.assertRaises(RootTrialGateError):evaluate(a,b,c)
    def test_stable_floor_is_not_gait_approval(self):
        a,b,c=self.fixture();x=evaluate(a,b,c)
        self.assertEqual(x['verdict'],'PASS_FLOOR_AND_CONTINUITY_PROXY_ONLY')
        self.assertFalse(x['gait_accepted'])
    def test_height_jerk_is_red(self):
        a,b,c=self.fixture();y=c['actors']['AsterOriginal']['required_root_y_clearance_m'];y[36]=.019
        a['root_channels'][0].update(max_lift_m=.019,max_step_m=.009)
        x=evaluate(a,b,c)
        self.assertEqual(x['verdict'],'RED_ROOT_Y_JERK')
    def test_penetration_red(self):
        a,b,c=self.fixture();row=b['per_side']['JuniperOriginal'][0];row.update(min_y_m=-.01,vertices_below_minus_5mm=1)
        b['summary']['JuniperOriginal'].update(worst_shoe_y_m=-.01,mean_stance_min_y_m=-.01/72,frames_shoe_below_minus_5mm=1)
        self.assertEqual(evaluate(a,b,c)['verdict'],'RED_FLOOR_PENETRATION')
    def test_hover_red(self):
        a,b,c=self.fixture()
        for row in b['per_side']['JuniperOriginal'][:2]:row.update(min_y_m=.02,vertices_within_10mm_floor=0)
        b['summary']['JuniperOriginal'].update(frames_both_feet_over_plus_10mm=1,mean_stance_min_y_m=.02/72)
        self.assertEqual(evaluate(a,b,c)['verdict'],'RED_FOOT_FLOATING')
    def test_bad_receipt_sha(self):self.bad(lambda a,b,c:a.update(source_sha256='0'*64))
    def test_bad_after_sha(self):self.bad(lambda a,b,c:b.update(source_sha256='1'*64))
    def test_fake_gait(self):self.bad(lambda a,b,c:b.update(gait_accepted=True))
    def test_fake_native(self):self.bad(lambda a,b,c:a.update(native_blender_evaluated=True))
    def test_fake_skin_preservation(self):self.bad(lambda a,b,c:a.update(source_skin_unchanged=False))
    def test_root_channel_missing(self):self.bad(lambda a,b,c:a['root_channels'].pop())
    def test_duplicate_root_actor(self):self.bad(lambda a,b,c:a['root_channels'][1].update(actor='AsterOriginal'))
    def test_identical_source_and_new_accessor(self):self.bad(lambda a,b,c:a['root_channels'][0].update(new_accessor=20))
    def test_missing_sample(self):self.bad(lambda a,b,c:b['per_side']['JuniperOriginal'].pop())
    def test_duplicate_sample(self):self.bad(lambda a,b,c:b['per_side']['AsterOriginal'].__setitem__(-1,b['per_side']['AsterOriginal'][0]))
    def test_false_counter(self):self.bad(lambda a,b,c:b['per_side']['JuniperOriginal'][0].update(vertices_below_minus_5mm=100))
    def test_wrong_summary(self):self.bad(lambda a,b,c:b['summary']['AsterOriginal'].update(worst_shoe_y_m=-.014))
    def test_fake_bounds(self):self.bad(lambda a,b,c:a['root_channels'][0].update(max_step_m=.021))
    def test_wrong_sole_source(self):self.bad(lambda a,b,c:c.update(source_sha256='2'*64))
    def test_nonfinite_height(self):self.bad(lambda a,b,c:c['actors']['JuniperOriginal']['required_root_y_clearance_m'].__setitem__(0,float('nan')))
    def test_false_derived_hash(self):self.bad(lambda a,b,c:a.update(derived_sha256='z'*64))
    def test_after_root_trial_not_run(self):self.bad(lambda a,b,c:b.update(root_y_trial_executed=False))

if __name__=='__main__':unittest.main()
