import json
import math
from pathlib import Path
import tempfile
import unittest

from motion_math import (
    G, froude, stride_frequency, minimum_jerk, swing_arc,
    two_link_knee, contact_speed, coordination_index,
    audit_corpus, audit_case
)

ROOT=Path(__file__).resolve().parent/'runs'

class ParametricMotionMathTests(unittest.TestCase):
    def test_froude_dimensionless(self):
        self.assertAlmostEqual(froude(1.0, 1.0), 1/G, places=10)
    def test_froude_scale_similarity(self):
        self.assertAlmostEqual(froude(2.0,2.0), froude(math.sqrt(2)*2,4.0))
    def test_froude_invalid(self):
        for a,b in [(1,0),(1,float('nan')),(True,1),(-1,1)]:
            with self.assertRaises(ValueError): froude(a,b)
    def test_stride_relation(self):
        self.assertAlmostEqual(stride_frequency(1.2,0.6),2.0)
    def test_minimum_jerk_boundary_and_middle(self):
        self.assertAlmostEqual(minimum_jerk(0),0)
        self.assertAlmostEqual(minimum_jerk(.5),.5)
        self.assertAlmostEqual(minimum_jerk(1),1)
    def test_minimum_jerk_symmetry(self):
        for i in range(10):
            t=i/10
            self.assertAlmostEqual(minimum_jerk(t)+minimum_jerk(1-t),1)
    def test_minimum_jerk_out_of_range(self):
        for t in (1.1,-.1,True,float('inf')):
            with self.assertRaises(ValueError):minimum_jerk(t)
    def test_swing_endpoints_and_height(self):
        a=[0,0,0];b=[1,0,0]
        self.assertEqual(swing_arc(a,b,0,.2),a)
        self.assertAlmostEqual(swing_arc(a,b,.5,.2)[2],.2)
        self.assertAlmostEqual(swing_arc(a,b,1,.2)[0],1)
    def test_ik_bone_length_and_branch(self):
        hip=[0,0,1];ankle=[.1,0,.1]
        left=two_link_knee(hip,ankle,.53,.52,1)
        right=two_link_knee(hip,ankle,.53,.52,-1)
        for x in (left,right):
            self.assertAlmostEqual(math.dist(hip,x),.53,places=8)
            self.assertAlmostEqual(math.dist(x,ankle),.52,places=8)
        self.assertNotAlmostEqual(left[0],right[0])
    def test_ik_unreachable_not_clamped(self):
        with self.assertRaisesRegex(ValueError,'UNREACHABLE'):
            two_link_knee([0,0,1],[0,0,-3],.53,.52,1)
    def test_contact_speed(self):
        self.assertAlmostEqual(contact_speed([0,0,0],[.01,0,0],.05),.2)
        with self.assertRaises(ValueError): contact_speed([0,0,0],[.01,0,0],0)
    def test_swim_coordination(self):
        self.assertAlmostEqual(coordination_index(.5),0)
        self.assertLess(coordination_index(.3),0)
        self.assertGreater(coordination_index(.7),0)
    def test_full_original_corpus_detects_false_greens(self):
        report=audit_corpus(ROOT)
        self.assertEqual(report['case_count'],22)
        self.assertEqual(report['counts'],{'PASS':10,'FAIL':11,'UNKNOWN':1})
        names={r['case']:r for r in report['cases']}
        self.assertEqual(names['female_swimming_barefoot']['status'],'UNKNOWN')
        self.assertEqual(names['female_cartwheel_barefoot']['status'],'FAIL')
        self.assertEqual(names['male_walk_barefoot']['status'],'PASS')
    def test_source_copy_tampering_is_detected_by_sha(self):
        p=ROOT/'locomotion/male_walk_barefoot_ground_truth.json'
        with tempfile.TemporaryDirectory() as d:
            dup=Path(d)/p.name
            dup.write_bytes(p.read_bytes())
            before=audit_case(dup,{'male':(.54,.53),'female':(.52,.51)})
            source=json.loads(dup.read_text())
            source['frames'][6]['joints']['left_ankle'][0]+=.02
            dup.write_text(json.dumps(source))
            after=audit_case(dup,{'male':(.54,.53),'female':(.52,.51)})
            self.assertNotEqual(before['source_sha256'],after['source_sha256'])
            self.assertEqual(after['status'],'FAIL')

if __name__=='__main__': unittest.main()
