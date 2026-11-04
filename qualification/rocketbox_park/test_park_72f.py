"""Hostile source-only constraints: no camera-side trees or 72f/fake product success."""
import unittest
from park_72f import check_park_geometry, FRAMES, FPS, TREE_COORDS, SCHEMA


class OriginalParkGeometryGuard(unittest.TestCase):
    def test_actual_author_procedural_park_is_clear(self):
        self.assertEqual(len(check_park_geometry(TREE_COORDS)), 7)

    def test_reject_no_trees(self):
        with self.assertRaisesRegex(ValueError, "NO_PARK_TREES"):
            check_park_geometry([])

    def test_reject_tree_in_actor_lane(self):
        with self.assertRaisesRegex(ValueError, "TREE_IN_ACTOR_OR_CAMERA_FOREGROUND"):
            check_park_geometry([(0, 0.2)])

    def test_reject_near_actor_framing(self):
        with self.assertRaisesRegex(ValueError, "TREE_IN_TWO_ACTOR_ACTION_FRAMING"):
            check_park_geometry([(1.1, 3.2)])

    def test_reject_duplicate_source_tree(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_PARK_TREE"):
            check_park_geometry([(4, 5), (4, 5)])

    def test_reject_negative_camera_side(self):
        with self.assertRaisesRegex(ValueError, "TREE_IN_ACTOR_OR_CAMERA_FOREGROUND"):
            check_park_geometry([(5, -10)])

    def test_reject_nan(self):
        with self.assertRaisesRegex(ValueError, "NONFINITE_TREE_COORDINATE"):
            check_park_geometry([(5, float("nan"))])

    def test_reject_inf(self):
        with self.assertRaisesRegex(ValueError, "NONFINITE_TREE_COORDINATE"):
            check_park_geometry([(5, float("inf"))])

    def test_reject_boolean_coercion(self):
        with self.assertRaisesRegex(ValueError, "NONFINITE_TREE_COORDINATE"):
            check_park_geometry([(True, 5)])

    def test_reject_invalid_shape(self):
        with self.assertRaisesRegex(ValueError, "INVALID_TREE_COORDINATE"):
            check_park_geometry([(1, 2, 3)])

    def test_reject_duplicate_after_numeric_normalization(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_PARK_TREE"):
            check_park_geometry([(5, 5), (5.0, 5.0)])

    def test_exact_source_clock(self):
        self.assertEqual((FRAMES, FPS), (72, 12))
        self.assertTrue(SCHEMA.endswith(".v1"))


if __name__ == "__main__":
    unittest.main()
