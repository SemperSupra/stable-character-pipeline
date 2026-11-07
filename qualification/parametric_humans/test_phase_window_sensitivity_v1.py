"""Source-free adversarial stance/swing temporal-proxy tests."""
import copy, unittest
from phase_window_sensitivity_v1 import evaluate, classify, OUT_SCHEMA, SCENARIOS
from foot_phase_reclassification_gate_v1 import PhaseEvidenceError

class PhaseSensitivityTest(unittest.TestCase):
    def fixture(self):
        from test_foot_phase_reclassification_gate_v1 import PhaseGateTest
        return PhaseGateTest().make()
    def test_valid_actor_matrix_no_biological_claim(self):
        w,p,r=self.fixture();out=evaluate(w,p,r)
        self.assertEqual(out['schema'],OUT_SCHEMA)
        self.assertEqual(len(out['scenarios']),5)
        self.assertFalse(out['stance_physics_certified'])
        self.assertFalse(out['persistent_shoe_vertex_ids_present'])
        self.assertFalse(out['natural_gait_accepted'])
        for scenario in out['scenarios']:
            for actor,data in scenario['actors'].items():
                for side in ('L','R'):
                    labels=data['labels'][side];self.assertEqual(len(labels),71)
                    self.assertEqual(sum(data['counts'][side].values()),71)
    def test_singleton_contact_stays_ambiguous(self):
        ankle=[[0.,0.,0.] for _ in range(72)]
        shoe=[0.]*72;root=[0.]*72
        prev=[{'persistent_vertices':0} for _ in range(71)]
        prev[20]['persistent_vertices']=10
        labels=classify(ankle,shoe,root,prev,.008,.008,2)
        self.assertEqual(labels[20],'ambiguous')
    def test_two_consecutive_contacts_are_proxy_only(self):
        ankle=[[0.,0.,0.] for _ in range(72)]
        prev=[{'persistent_vertices':0} for _ in range(71)]
        prev[15]['persistent_vertices']=5;prev[16]['persistent_vertices']=5
        labels=classify(ankle,[0.]*72,[0.]*72,prev,.008,.008,2)
        self.assertEqual(labels[15:17],['stance_proxy','stance_proxy'])
        self.assertEqual(labels[14],'ambiguous')
    def test_swing_motion_not_planted(self):
        ankle=[[float(i)*.02,0.,0.] for i in range(72)]
        labels=classify(ankle,[0.]*72,[0.]*72,[{'persistent_vertices':5}]*71,.008,.008,2)
        self.assertEqual(set(labels),{'swing_proxy'})
    def test_far_sole_not_planted(self):
        ankle=[[0.,0.,0.]]*72
        labels=classify(ankle,[.025]*72,[0.]*72,[{'persistent_vertices':8}]*71,.008,.008,2)
        self.assertEqual(set(labels),{'swing_proxy'})
    def test_strict_source(self):
        w,p,r=self.fixture();w['source_sha256']='0'*64
        with self.assertRaises(PhaseEvidenceError):evaluate(w,p)
    def test_strict_prior_bytes(self):
        w,p,r=self.fixture()
        with self.assertRaises(PhaseEvidenceError):evaluate(w,p,r+b' ')
    def test_mutated_ankle_nonfinite(self):
        w,p,r=self.fixture();w['actors']['AsterOriginal']['ankle_world_xyz_m']['L'][8][0]=float('nan')
        with self.assertRaises(PhaseEvidenceError):evaluate(w,p)
    def test_false_approval(self):
        w,p,r=self.fixture();w['gait_accepted']=True
        with self.assertRaises(PhaseEvidenceError):evaluate(w,p)
    def test_no_extra_shoe_side(self):
        w,p,r=self.fixture();w['actors']['JuniperOriginal']['shoe_min_y_m']['C']=[0.]*72
        with self.assertRaises(PhaseEvidenceError):evaluate(w,p)
    def test_minrun_nonintegral_rejected(self):
        with self.assertRaises(PhaseEvidenceError): classify([[0.,0.,0.]]*72,[0.]*72,[0.]*72,[{'persistent_vertices':5}]*71,.008,.008,6)
if __name__=='__main__':unittest.main()
