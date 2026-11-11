import hashlib
import json
import math
import unittest
from run_matrix import aggregate, valid_pose, case_map

class IndependentModalContractTest(unittest.TestCase):
    def test_positive_all_judges(self):
        self.assertEqual(aggregate(['PASS','PASS']),'PASS')
    def test_any_fail_dominates(self):
        for a in ('PASS','UNKNOWN','FAIL'):
            self.assertEqual(aggregate([a,'FAIL']),'FAIL')
            self.assertEqual(aggregate(['FAIL',a]),'FAIL')
    def test_unknown_not_averaged_into_pass(self):
        self.assertEqual(aggregate(['PASS','UNKNOWN']),'UNKNOWN')
    def test_missing_judge_rejected(self):
        for values in ([],['PASS','ERROR'],['PASS',None]):
            with self.assertRaisesRegex(ValueError,'INVALID'):
                aggregate(values)
    def test_case_ids_unique(self):
        names=[c['id'] for c in case_map()]
        self.assertEqual(len(names),len(set(names)))
        self.assertEqual(len(names),6)
    def test_counterfactuals_include_independent_domain_failures(self):
        m={c['id']:c['want'] for c in case_map()}
        self.assertEqual(m['knee_reversal'],{'temporal':'PASS','geometry':'FAIL','overall':'FAIL'})
        self.assertEqual(m['luma_flicker'],{'temporal':'FAIL','geometry':'PASS','overall':'FAIL'})
        self.assertEqual(m['scene_cut_abstain']['overall'],'UNKNOWN')
    def test_anatomy_source_is_deterministic(self):
        a=valid_pose()
        b=valid_pose()
        self.assertEqual(json.dumps(a,sort_keys=True),json.dumps(b,sort_keys=True))
        self.assertTrue(math.isclose(a['segment_lengths_m'][1],math.hypot(.1,.45)))
    def test_original_source_has_no_person_data(self):
        pose=valid_pose()
        self.assertEqual(len(pose['frames']),8)
        self.assertNotIn('name',pose)
        self.assertTrue(pose['approved_bend_pole'])
    def test_fabricated_pose_change_is_distinct_case(self):
        base=valid_pose()
        flipped=valid_pose()
        flipped['frames'][3]['ankle'][0]=-.1
        self.assertNotEqual(hashlib.sha256(json.dumps(base,sort_keys=True).encode()).digest(),
                            hashlib.sha256(json.dumps(flipped,sort_keys=True).encode()).digest())

if __name__=='__main__':unittest.main()
