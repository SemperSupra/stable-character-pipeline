"""Adversarial source-original URDF parser qualification with no outside packages."""
import unittest
from urdf_observe import read_model

GOOD='''<robot name="original-test">
<link name="base"/><link name="arm"/><link name="follower"/>
<joint name="hinge" type="revolute">
 <parent link="base"/><child link="arm"/>
 <axis xyz="0 0 1"/>
 <limit lower="-1" upper="1" velocity="2" effort="10"/>
</joint>
<joint name="follower_joint" type="revolute">
 <parent link="arm"/><child link="follower"/>
 <axis xyz="0 0 1"/>
 <limit lower="-1" upper="1" velocity="2" effort="10"/>
 <mimic joint="hinge" multiplier="-1" offset="0"/>
</joint>
</robot>'''
class OriginalRobotTests(unittest.TestCase):
    def test_pinned_source_only(self):
        result=read_model(GOOD.encode())
        self.assertEqual(result["status"],"PROPOSED_MECHANISM_LIMITS_UNQUALIFIED")
        self.assertEqual(len(result["joints"]),2)
        self.assertTrue(result["source_sha256"])
        self.assertIn("thermal",result["unverified"])
    def test_wrong_topology(self):
        with self.assertRaisesRegex(ValueError,"PARENT_CHILD"):
            read_model(GOOD.replace('link="follower"','link="unknown"').encode())
    def test_wrong_mimic(self):
        with self.assertRaisesRegex(ValueError,"MIMIC_SOURCE"):
            read_model(GOOD.replace('mimic joint="hinge"','mimic joint="missing"').encode())
    def test_missing_hard_stop(self):
        with self.assertRaisesRegex(ValueError,"MISSING_HARD_RANGE"):
            read_model(GOOD.replace('lower="-1" upper="1"','',1).encode())
    def test_inverted_joint_stop(self):
        with self.assertRaisesRegex(ValueError,"INVALID_HARD_RANGE"):
            read_model(GOOD.replace('lower="-1" upper="1"','lower="2" upper="1"',1).encode())
    def test_invalid_velocity_or_effort(self):
        with self.assertRaisesRegex(ValueError,"INVALID_VELOCITY_EFFORT"):
            read_model(GOOD.replace('velocity="2"','velocity="0"',1).encode())
    def test_reject_dtd_entities(self):
        with self.assertRaisesRegex(ValueError,"UNADMITTED_URDF_XML"):
            read_model(('<!DOCTYPE robot [<!ENTITY foo "x">]>'+GOOD).encode())
    def test_missing_source_axis(self):
        with self.assertRaisesRegex(ValueError,"INVALID_AXIS"):
            read_model(GOOD.replace('axis xyz="0 0 1"','axis xyz="0 0 0"',1).encode())
    def test_continuous_has_no_position_stop(self):
        with self.assertRaisesRegex(ValueError,"CONTINUOUS_HAS_POSITION_LIMIT"):
            read_model(GOOD.replace('type="revolute"','type="continuous"',1).encode())
    def test_source_duplicate_link_rejected(self):
        with self.assertRaisesRegex(ValueError,"UNQUALIFIED_LINK_SET"):
            read_model(GOOD.replace('<link name="base"/>','<link name="base"/><link name="base"/>').encode())
if __name__=="__main__":
    unittest.main()
