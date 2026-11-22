"""Independent source-window geometry and clock tests; pinned real BVH only in CI."""
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from window_doe import edge_metrics,window_summary,STARTS

def coords():
    return [(float(i),0.,0.) for i in range(242)]  # input centimetres

class SourceWindowTests(unittest.TestCase):
    def test_original_window_start_120_uses_120_121(self):
        x=window_summary(coords(),120)
        self.assertEqual(x["source_window_start"],120)
        self.assertEqual(x["first_edge"],"120->121")
        self.assertEqual(x["preceding_edge"],"119->120")
        self.assertAlmostEqual(x["first_edge_speed_3d_mps"],.6)
        self.assertEqual(x["start_does_not_prove_target_retarget_clock"],True)

    def test_offbyone_boundary_variants_independent(self):
        self.assertEqual(STARTS,(119,120,121,122,180))
        x=coords()
        x[122]=(122.,0.,50.)
        a=window_summary(x,120)
        b=window_summary(x,121)
        self.assertLess(a["first_edge_speed_3d_mps"],b["first_edge_speed_3d_mps"])
        self.assertGreater(a["next_edge_speed_3d_mps"],a["first_edge_speed_3d_mps"])

    def test_y_up_source_is_not_horizontal(self):
        x=edge_metrics((0.,0.,0.),(0.,20.,0.))
        self.assertEqual(x["speed_horizontal_xz_mps"],0.)
        self.assertAlmostEqual(x["speed_3d_mps"],12.)

    def test_bvh_source_units_scaled_once(self):
        x=edge_metrics((0.,0.,0.),(0.,0.,1.))
        self.assertEqual(x["delta_xyz_m"],[0.,0.,.01])
        self.assertAlmostEqual(x["speed_3d_mps"],.6)

    def test_boolean_nan_and_invalid_dt_rejected(self):
        for bad in (math.nan,math.inf,True):
            with self.subTest(value=bad),self.assertRaises(ValueError):
                edge_metrics((0.,0.,0.),(bad,0.,0.))
        with self.assertRaises(ValueError):
            edge_metrics((0.,0.,0.),(1.,0.,0.),dt=0.)

    def test_bad_window_range_and_type_rejected(self):
        for bad in (0,True,182,300):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                window_summary(coords(),bad)

    def test_frame_start_shift_changes_actual_edge(self):
        x=coords()
        x[120]=(120.,0.,.5)
        a=window_summary(x,119)
        b=window_summary(x,120)
        self.assertNotEqual(a["first_edge_delta_xyz_m"],b["first_edge_delta_xyz_m"])

if __name__=="__main__":unittest.main()
