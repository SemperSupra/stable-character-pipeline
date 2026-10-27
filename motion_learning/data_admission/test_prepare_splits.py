import unittest
from prepare_splits import assign

def record(id, group, **kw):
    x = {"id": id, "domain": "fauna", "source_id": "synthetic",
         "source_group": group, "lineage_key": "synthetic-generator-v1",
         "skeleton_id": "quadruped17", "modality": "3d_points",
         "license_state": "self_authored", "admission_state": "admitted"}
    x.update(kw)
    return x

class TestSplitPlan(unittest.TestCase):
    def test_grouping_and_permutation(self):
        rows = [record("a","recording1"), record("b","recording1"),
                record("c","recording2")]
        plan = assign(rows)
        find = lambda key: next(k for k,v in plan.items() if key in v)
        self.assertEqual(find("a"), find("b"))
        self.assertEqual(assign(list(reversed(rows))), plan)
    def test_rights(self):
        with self.assertRaisesRegex(ValueError, "NOT_ADMITTED"):
            assign([record("a","r",admission_state="candidate")])
    def test_duplicates(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_RECORD_ID"):
            assign([record("a","r"), record("a","x")])
    def test_missing_lineage(self):
        with self.assertRaisesRegex(ValueError, "INVALID_LINEAGE_KEY"):
            assign([record("a","r",lineage_key="")])
    def test_domain(self):
        with self.assertRaisesRegex(ValueError, "INVALID_DOMAIN"):
            assign([record("a","r",domain="unknown")])
    def test_empty(self):
        with self.assertRaisesRegex(ValueError, "EMPTY_RECORD_SET"):
            assign([])

if __name__ == "__main__":
    unittest.main()
