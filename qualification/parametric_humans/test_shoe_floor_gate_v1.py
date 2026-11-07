import unittest
from shoe_floor_gate_v1 import gate,FloorGateError
from shoe_floor_contact_v1_schema import SCHEMA,INPUT_SHA256

class FloorContractTests(unittest.TestCase):
    def good(self,foot=-0.0005):
        actors={};summaries={}
        for actor in ('AsterOriginal','JuniperOriginal'):
            rows=[]
            for frame in range(72):
                for side in ('L','R'):
                    rows.append({'frame':frame,'side':side,'min_y_m':foot,'vertices':1000,
                     'vertices_below_minus_1mm':int(foot<-.001),'vertices_below_minus_5mm':int(foot<-.005),
                     'vertices_within_10mm_floor':20 if abs(foot)<.010 else 0})
            actors[actor]=rows
            summaries[actor]={'worst_min_y_m':foot,'stance_min_mean_y_m':foot,
                'frames_with_sole_below_minus_1mm':int(foot<-.001)*72,
                'frames_with_sole_below_minus_5mm':int(foot<-.005)*72,
                'foot_frame_count_below_minus_1mm':int(foot<-.001)*144,
                'frames_both_feet_above_plus_10mm':72 if foot>.010 else 0,
                'diagnostic_only_root_clearance_shift_m_min':-foot,
                'diagnostic_only_root_clearance_shift_m_max':-foot,
                'max_root_shift_delta_m_per_frame':0.0}
        return {'schema':SCHEMA,'source_sha256':INPUT_SHA256,'coordinate_up':'Y','floor_y_m':0.0,
            'actors':actors,'summary':summaries,'frames_evaluated':72,
            'root_shift_applied':False,'native_blender_evaluated':False,'physical_contact_accepted':False,
            'realistic_gait_accepted':False,'release_approved':False}
    def expect_bad(self,fn):
        a=self.good();fn(a)
        with self.assertRaises(FloorGateError):gate(a)
    def test_floor_proxy_pass_has_no_physical_claim(self):
        r=gate(self.good());self.assertEqual(r['verdict'],'PASS_FLOOR_DISTANCE_PROXY_ONLY');self.assertFalse(r['realistic_gait_accepted'])
    def test_floor_penetration_rejected(self):
        r=gate(self.good(-.008));self.assertEqual(r['verdict'],'RED_FOOT_FLOOR_PENETRATION');self.assertEqual(len(r['rejects']),2)
    def test_hovering_both_feet_rejected(self):
        r=gate(self.good(.09));self.assertEqual(r['verdict'],'RED_FOOT_FLOATING');self.assertEqual(len(r['hovering']),2)
    def test_wrong_source(self):self.expect_bad(lambda a:a.update(source_sha256='0'*64))
    def test_wrong_axis(self):self.expect_bad(lambda a:a.update(coordinate_up='Z'))
    def test_fake_release(self):self.expect_bad(lambda a:a.update(release_approved=True))
    def test_fake_native(self):self.expect_bad(lambda a:a.update(native_blender_evaluated=True))
    def test_fake_root_correction(self):self.expect_bad(lambda a:a.update(root_shift_applied=True))
    def test_missing_frame(self):self.expect_bad(lambda a:a['actors']['AsterOriginal'].pop())
    def test_duplicate_frame(self):self.expect_bad(lambda a:a['actors']['AsterOriginal'].__setitem__(-1,a['actors']['AsterOriginal'][0]))
    def test_bogus_summary(self):self.expect_bad(lambda a:a['summary']['AsterOriginal'].__setitem__('worst_min_y_m',0.01))
    def test_nonfinite(self):self.expect_bad(lambda a:a['actors']['JuniperOriginal'][0].__setitem__('min_y_m',float('nan')))
    def test_bogus_near_floor_counter(self):self.expect_bad(lambda a:a['actors']['AsterOriginal'][0].__setitem__('vertices_within_10mm_floor',9999))
    def test_bogus_counter(self):self.expect_bad(lambda a:a['actors']['JuniperOriginal'][0].__setitem__('vertices_below_minus_5mm',90))
if __name__=='__main__':unittest.main()
