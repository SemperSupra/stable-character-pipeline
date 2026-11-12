"""Fail-closed, dependency-free metamorphic tests for contact identifiability."""
import math
import unittest
from contact_cover import minimum_cover_dp, maximum_matching_path, sliding_edges

class ContactCoverTests(unittest.TestCase):
    def test_full_sliding_path_is_not_all_contact(self):
        edges = list(range(39))
        count, witness = minimum_cover_dp(edges, 40)
        self.assertEqual(count, 20)  # forty path vertices, 39 sliding edges
        self.assertTrue(all(i in witness or i+1 in witness for i in edges))
        self.assertEqual(maximum_matching_path(edges, 40)[0], count)

    def test_all_path_subsets_two_independent_exact_oracles(self):
        for mask in range(1 << 8):
            edges = [i for i in range(8) if mask & (1 << i)]
            a, witness = minimum_cover_dp(edges, 9)
            b, matching = maximum_matching_path(edges, 9)
            self.assertEqual(a, b, (edges, witness, matching))
            self.assertEqual(len(witness), len(set(witness)))
            self.assertTrue(all(i in witness or i+1 in witness for i in edges))

    def test_static_planted_ankles_require_zero_relabels(self):
        frames = [{"contact":{"left":True},
                   "joints":{"left_ankle":[0.,0.,0.]}} for _ in range(40)]
        self.assertEqual(sliding_edges(frames, "left"), [])
        self.assertEqual(minimum_cover_dp([], 40), (0, []))

    def test_one_bad_interval_requires_one_label_change(self):
        frames = [{"contact":{"left":True},
                   "joints":{"left_ankle":[0.,0.,0.]}},
                  {"contact":{"left":True},
                   "joints":{"left_ankle":[0.1,0.,0.]}},
                  {"contact":{"left":True},
                   "joints":{"left_ankle":[0.1,0.,0.]}}]
        self.assertEqual(sliding_edges(frames, "left"), [0])
        self.assertEqual(minimum_cover_dp([0], 3)[0], 1)

    def test_unknown_contact_is_rejected_not_filled(self):
        frames = [{"contact":{"left":True},"joints":{"left_ankle":[0.,0.,0.]}},
                  {"contact":{"left":1},"joints":{"left_ankle":[.1,0.,0.]}}]
        with self.assertRaisesRegex(ValueError, "BAD_CONTACT_BOOLEAN"):
            sliding_edges(frames, "left")

    def test_nonfinite_coordinates_fail_closed(self):
        frames = [{"contact":{"left":True},"joints":{"left_ankle":[0.,0.,0.]}},
                  {"contact":{"left":True},"joints":{"left_ankle":[math.nan,0.,0.]}}]
        with self.assertRaisesRegex(ValueError, "INVALID_WORLD_ANKLE"):
            sliding_edges(frames, "left")

    def test_bad_frame_edge_rejected(self):
        for edge in ([-1], [39], [True]):
            with self.assertRaisesRegex(ValueError, "INVALID_EDGES"):
                minimum_cover_dp(edge, 40)
            with self.assertRaisesRegex(ValueError, "INVALID_EDGES"):
                maximum_matching_path(edge, 40)

if __name__ == "__main__":
    unittest.main()
