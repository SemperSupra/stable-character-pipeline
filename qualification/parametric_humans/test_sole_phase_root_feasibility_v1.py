"""Source-free hostile test corpus for the foot-lock feasibility gate."""
import copy,math,unittest
from sole_phase_root_feasibility_v1 import (SCHEMA,SOURCE_SHA256,evaluate,FeasibilityError)

class SolePhaseTests(unittest.TestCase):
    def fixture(self,left=(.002,0.),right=(.002,0.),dual=True):
        actors={}
        for a in ('AsterOriginal','JuniperOriginal'):
            rows=[]
            for i in range(1,72):
                foot={}
                for side,vec in (('L',left),('R',right)):
                    if not dual and side=='R':foot[side]={'persistent_vertices':2}
                    else:foot[side]={'persistent_vertices':9,'median_xz_motion_m':list(vec),
                         'p95_rigid_translation_residual_m':.001,'median_sliding_m':.002}
                rows.append({'frame_to':i,'feet':foot,
                    'dual_support_root_motion_disagreement_m':math.dist(left,right) if dual else None})
            dualdist=math.dist(left,right)
            actors[a]={'required_root_y_clearance_m':[.01]*72,'transitions':rows,
                'dual_contact_transitions':71 if dual else 0,
                'dual_root_xz_disagreement_max_m':dualdist if dual else None,
                'dual_root_xz_disagreement_p95_m':dualdist if dual else None,
                'persistent_foot_transitions':142 if dual else 71,
                'root_y_clearance_periodic_jump_m':0.}
        return {'schema':SCHEMA,'source_sha256':SOURCE_SHA256,'frames':72,
            'coordinate_up':'Y','root_shift_applied':False,'native_blender_evaluated':False,
            'gait_accepted':False,'release_approved':False,'actors':actors}
    def reject(self,mutation):
        f=self.fixture();mutation(f)
        with self.assertRaises(FeasibilityError):evaluate(f)
    def test_proxy_pass_not_real_gait(self):
        q=evaluate(self.fixture());self.assertEqual(q['verdict'],'PASS_ROOT_TRANSLATION_FEASIBILITY_PROXY_ONLY')
        self.assertFalse(q['gait_accepted']);self.assertFalse(q['foot_lock_accepted'])
    def test_root_only_conflict_bilateral_lower_bound(self):
        q=evaluate(self.fixture((.12,0), (0,0)))
        self.assertEqual(q['verdict'],'RED_ROOT_TRANSLATION_ONLY_CONFLICT')
        self.assertAlmostEqual(q['actors']['AsterOriginal']['root_translation_only_lower_bound_max_slip_m'],.06)
        self.assertEqual(q['actors']['JuniperOriginal']['conflicting_dual_support_transitions'],71)
    def test_sparse_hold_not_green(self):
        self.assertEqual(evaluate(self.fixture(dual=False))['verdict'],'HOLD_NO_DUAL_CONTACT_EVIDENCE')
    def test_stale_source(self):self.reject(lambda f:f.update(source_sha256='0'*64))
    def test_wrong_axis(self):self.reject(lambda f:f.update(coordinate_up='Z'))
    def test_missing_frame(self):self.reject(lambda f:f['actors']['AsterOriginal']['transitions'].pop())
    def test_duplicate_frame(self):self.reject(lambda f:f['actors']['AsterOriginal']['transitions'][1].update(frame_to=1))
    def test_missing_foot(self):self.reject(lambda f:f['actors']['JuniperOriginal']['transitions'][0]['feet'].pop('R'))
    def test_forged_release(self):self.reject(lambda f:f.update(release_approved=True))
    def test_forged_native(self):self.reject(lambda f:f.update(native_blender_evaluated=True))
    def test_forged_shift(self):self.reject(lambda f:f.update(root_shift_applied=True))
    def test_forged_gait(self):self.reject(lambda f:f.update(gait_accepted=True))
    def test_nonfinite(self):self.reject(lambda f:f['actors']['AsterOriginal']['transitions'][0]['feet']['L']['median_xz_motion_m'].__setitem__(0,float('nan')))
    def test_false_dual_measure(self):self.reject(lambda f:f['actors']['AsterOriginal']['transitions'][0].update(dual_support_root_motion_disagreement_m=0.12))
    def test_false_conflict_summary(self):self.reject(lambda f:f['actors']['AsterOriginal'].update(dual_root_xz_disagreement_max_m=.22))
    def test_counterfeit_insufficient(self):self.reject(lambda f:f['actors']['AsterOriginal'].update(persistent_foot_transitions=0))
    def test_discontinuous_lift_receipt(self):self.reject(lambda f:f['actors']['AsterOriginal']['required_root_y_clearance_m'].__setitem__(0,.02))

if __name__=='__main__':unittest.main()
