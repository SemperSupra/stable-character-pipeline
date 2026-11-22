"""Hostile source-only 100STYLE first-edge FK contract; no synthetic source admission."""
import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
from first_edge_source import first_edge_metrics


def fixture():
    return [(0.0,float(i),0.0) for i in range(180)]  # input source centimetres


class SourceFkAdversarial(unittest.TestCase):
    def test_correct_source_cm_m_and_si_velocity(self):
        r=first_edge_metrics(fixture())
        self.assertEqual(r["source_first_edge"],"120->121")
        self.assertAlmostEqual(r["source_first_edge_3d_speed_mps"],0.6,places=7)
        self.assertAlmostEqual(r["first_59_edges_3d_speed_median_mps"],0.6,places=7)
        self.assertEqual(r["source_first_edge_horizontal_xz_speed_mps"],0.0)
        self.assertFalse(r["native_retarged_footwear_accepted"])

    def test_first_edge_outlier_cannot_be_hidden_by_median(self):
        x=fixture()
        x[121]=(0.0,3.0,0.0)
        r=first_edge_metrics(x)
        self.assertGreater(r["first_edge_to_median_ratio"],1.5)
        self.assertAlmostEqual(r["source_first_edge_3d_speed_mps"],70.8)

    def test_native_source_xz_horizontal_is_not_y(self):
        x=fixture()
        x[121]=(50.,121.,0.)
        r=first_edge_metrics(x)
        self.assertAlmostEqual(r["source_first_edge_horizontal_xz_speed_mps"],30.0)

    def test_corrupt_point_rejected(self):
        for bad in (math.nan,math.inf,True,"3.14"):
            x=fixture()
            x[121]=(0.,bad,0.)
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                first_edge_metrics(x)

    def test_short_and_forged_start_rejected(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_FK_SERIES_SHORT"):
            first_edge_metrics(fixture()[:-1])
        with self.assertRaisesRegex(ValueError,"SOURCE_FK_INVALID_FIRST_EDGE"):
            first_edge_metrics(fixture(),start=121)
        with self.assertRaisesRegex(ValueError,"SOURCE_FK_INVALID_FIRST_EDGE"):
            first_edge_metrics(fixture(),start=True)

    def test_observed_first_edge_uses_original_120_121(self):
        x=fixture()
        x[119]=(0.,99.,0.)
        x[120]=(0.,100.,0.)
        x[121]=(0.,101.,0.)
        r=first_edge_metrics(x)
        self.assertAlmostEqual(r["source_first_edge_3d_speed_mps"],0.6)
        self.assertEqual(r["source_first_edge_world_xyz_m"],[0.,.01,0.])


if __name__=="__main__":
    unittest.main()
