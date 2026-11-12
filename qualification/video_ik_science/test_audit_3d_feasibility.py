import math
import unittest
from audit_3d_feasibility import solve_3d

class ThreeDTwoLinkFalsifiers(unittest.TestCase):
    def test_full_3d_y_separation_has_exact_lengths(self):
        # A valid out-of-plane endpoint cannot be handled by x/z-only solver.
        hip=[0.0,0.0,0.8]
        ankle=[0.1,0.2,0.1]
        old=[0.2,0.0,0.45]
        row=solve_3d(hip,ankle,.54,.53,old)
        self.assertEqual(row["status"],"FEASIBLE")
        self.assertGreater(row["off_plane_endpoint_displacement_m"],.19)
        self.assertLessEqual(row["candidate_knee_bone_error_m"],1e-7)

    def test_unreachable_not_clamped(self):
        row=solve_3d([0,0,2],[0,0,0],.54,.53,[.1,0,1])
        self.assertEqual(row["status"],"UNREACHABLE")
        self.assertNotIn("candidate_knee_xyz",row)

    def test_nonfinite_and_bool_rejected(self):
        for bad in ([float("nan"),0,0],[True,0,0],[float("inf"),0,0]):
            with self.assertRaisesRegex(ValueError,"NONFINITE_JOINT"):
                solve_3d(bad,[0,0,0],.54,.53,[.1,0,.1])

    def test_too_close_endpoints_abstain(self):
        row=solve_3d([0,0,0],[0,0,0],.54,.53,[.1,0,.1])
        self.assertEqual(row["status"],"UNREACHABLE")

    def test_degenerate_reference_switch(self):
        row=solve_3d([0,0.0,0],[0,.85,0],.54,.53,[.1,.45,0])
        self.assertEqual(row["status"],"FEASIBLE")
        self.assertLessEqual(row["candidate_knee_bone_error_m"],1e-7)

if __name__=="__main__":
    unittest.main()
