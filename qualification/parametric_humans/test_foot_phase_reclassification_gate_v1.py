"""Public-safe hostile tests for phase reclassification; no source GLBs."""
from __future__ import annotations
import copy
import hashlib
import json
import math
import unittest
from foot_phase_reclassification_gate_v1 import (
    evaluate, PhaseEvidenceError, SOURCE_SHA256, OLD_SCHEMA, SCHEMA,
)

class PhaseGateTest(unittest.TestCase):
    def make(self):
        actors_w, actors_p = {}, {}
        for actor in ('AsterOriginal', 'JuniperOriginal'):
            ankle_l = [[float(i)*.001, .15, 0.] for i in range(72)]
            ankle_r = [[float(i)*.001, .15, .25] for i in range(72)]
            # One false-old-dual step: right foot moving 50 mm; left static.
            ankle_l[0] = [0., .15, 0.]
            ankle_l[1] = [0., .15, 0.]
            ankle_r[0] = [0., .15, .25]
            ankle_r[1] = [.05, .15, .25]
            rows = []
            for f in range(1, 72):
                foot = {s: {'persistent_vertices': 6,
                             'median_xz_motion_m': [0., 0.],
                             'p95_rigid_translation_residual_m': 0.,
                             'median_sliding_m': 0.}
                        for s in ('L', 'R')}
                delta = 0.
                if f == 1:
                    foot['R']['median_xz_motion_m'] = [.05, 0.]
                    foot['R']['median_sliding_m'] = .05
                    delta = .05
                rows.append({'frame_to': f, 'feet': foot,
                             'dual_support_root_motion_disagreement_m': delta})
            actors_w[actor] = {
                'ankle_world_xyz_m': {'L': ankle_l, 'R': ankle_r},
                'shoe_min_y_m': {'L': [-.01]*72, 'R': [-.01]*72},
                'diagnostic_root_lift_m': [.01]*72,
            }
            actors_p[actor] = {
                'transitions': rows,
                'required_root_y_clearance_m': [.01]*72,
            }
        prior = {'schema': OLD_SCHEMA, 'source_sha256': SOURCE_SHA256,
                 'coordinate_up': 'Y', 'frames': 72, 'actors': actors_p,
                 'root_shift_applied': False, 'native_blender_evaluated': False,
                 'gait_accepted': False, 'release_approved': False}
        raw = json.dumps(prior, sort_keys=True).encode()
        witness = {'schema': SCHEMA, 'source_sha256': SOURCE_SHA256,
                   'coordinate_up': 'Y', 'frames': 72, 'actors': actors_w,
                   'shoe_support_sha256': '1'*64,
                   'sole_correspondence_sha256': hashlib.sha256(raw).hexdigest(),
                   'root_shift_applied': False, 'foot_ik_applied': False,
                   'native_blender_evaluated': False, 'gait_accepted': False,
                   'release_approved': False}
        return witness, prior, raw

    def reject(self, fn):
        w,p,r = self.make()
        fn(w,p)
        with self.assertRaises(PhaseEvidenceError):
            evaluate(w,p)

    def test_false_dual_reclassified(self):
        w,p,r = self.make()
        o = evaluate(w,p,r)
        self.assertEqual(o['verdict'], 'CORRECT_PRIOR_DUAL_CONTACT_CONFOUND_RESEARCH_ONLY')
        for actor in o['actors']:
            self.assertEqual(o['actors'][actor]['old_conflicts'], 1)
            self.assertEqual(o['actors'][actor]['old_conflicts_reclassified_as_moving_foot'], 1)
            self.assertFalse(o['root_only_impossibility_proven'])
            self.assertFalse(o['gait_accepted'])
    def test_dual_stillness_no_false_claim(self):
        w,p,_ = self.make()
        for actor in w['actors']:
            w['actors'][actor]['ankle_world_xyz_m']['R'][1] = [0., .15, .25]
            p['actors'][actor]['transitions'][0]['feet']['R']['median_xz_motion_m'] = [0., 0.]
            p['actors'][actor]['transitions'][0]['feet']['R']['median_sliding_m'] = 0.
            p['actors'][actor]['transitions'][0]['dual_support_root_motion_disagreement_m'] = 0.
        o = evaluate(w,p)
        self.assertEqual(o['verdict'], 'HOLD_NO_PRIOR_CONFOUND_EVIDENCE')
        self.assertFalse(o['gait_accepted'])
    def test_wrong_witness_source(self):self.reject(lambda w,p:w.update(source_sha256='0'*64))
    def test_wrong_prior_source(self):self.reject(lambda w,p:p.update(source_sha256='0'*64))
    def test_axis_attack(self):self.reject(lambda w,p:w.update(coordinate_up='Z'))
    def test_frame_count_attack(self):self.reject(lambda w,p:w.update(frames=71))
    def test_missing_actor(self):self.reject(lambda w,p:w['actors'].pop('JuniperOriginal'))
    def test_wrong_shoe_digest(self):self.reject(lambda w,p:w.update(shoe_support_sha256='zzzz'))
    def test_fake_gait(self):self.reject(lambda w,p:w.update(gait_accepted=True))
    def test_fake_blender(self):self.reject(lambda w,p:w.update(native_blender_evaluated=True))
    def test_fake_foot_ik(self):self.reject(lambda w,p:w.update(foot_ik_applied=True))
    def test_fake_root(self):self.reject(lambda w,p:w.update(root_shift_applied=True))
    def test_fake_release(self):self.reject(lambda w,p:w.update(release_approved=True))
    def test_fake_prior_release(self):self.reject(lambda w,p:p.update(release_approved=True))
    def test_missing_ankle_sample(self):self.reject(lambda w,p:w['actors']['AsterOriginal']['ankle_world_xyz_m']['L'].pop())
    def test_nonfinite_ankle(self):self.reject(lambda w,p:w['actors']['AsterOriginal']['ankle_world_xyz_m']['R'][4].__setitem__(0,float('nan')))
    def test_prior_height_mismatch(self):self.reject(lambda w,p:p['actors']['JuniperOriginal']['required_root_y_clearance_m'].__setitem__(4,.02))
    def test_shoe_ground_mismatch(self):self.reject(lambda w,p:w['actors']['JuniperOriginal']['shoe_min_y_m']['L'].__setitem__(4,-.04))
    def test_noncontiguous_transitions(self):self.reject(lambda w,p:p['actors']['JuniperOriginal']['transitions'][2].update(frame_to=90))
    def test_forged_prior_disagreement(self):self.reject(lambda w,p:p['actors']['JuniperOriginal']['transitions'][0].update(dual_support_root_motion_disagreement_m=.1))
    def test_extra_shoe(self):self.reject(lambda w,p:w['actors']['AsterOriginal']['shoe_min_y_m'].update(C=[0.]*72))
    def test_digest_raw_pin(self):
        w,p,r=self.make()
        with self.assertRaises(PhaseEvidenceError):evaluate(w,p,r+b'\n')

if __name__=='__main__':unittest.main()
