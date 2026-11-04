"""Hostile fixture tests: axis receipts never become physical gait admission."""
import copy
import math
import unittest
from probe_axes import ROOTS, SCHEMA, SOURCE_SHA
from verify_probe import check, Rejected


def fixture():
    records={}
    for root in ROOTS:
        records[root]={"armature":root+"_armature","bone_count":80}
    rows=[]
    for root in ROOTS:
        for side in ("L","R"):
            for joint in ("Thigh","Calf"):
                for axis in "XYZ":
                    delta=[.01, .0, .0] if axis=="X" else [.0,.01,.0]
                    rows.append({
                        "actor":root,"side":side,"joint":joint,"local_axis":axis,
                        "sampled_frame":36,"perturb_radians":.35,
                        "sampled_source_skin_vertices":24,"human_sagittal_axis_certified":False,
                        "source_rest_matrix3":[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],
                        "baseline_foot_region_world_xyz":[0.,0.,0.],
                        "perturbed_foot_region_world_xyz":delta.copy(),
                        "observed_skinned_world_displacement_xyz":delta.copy(),
                        "observed_displacement_m":.01,
                    })
    return {
        "schema":SCHEMA,"status":"NATIVE_MIT_SKIN_AXIS_DIAGNOSTIC_ONLY",
        "source_blend_sha256":SOURCE_SHA,"frame":36,"fps":12,
        "rig_owners":records,"axis_probes":rows,
        "max_actual_weighted_foot_motion_m":.01,
        "native_source_skin_motion_observed":True,
        "signed_joint_coordinate_system":"NOT_CALIBRATED",
        "foot_contact":"UNKNOWN","real_world_sagittal_basis":"UNKNOWN",
        "original_naomi_alison_mvp":False,"product_accepted":False,
    }


class AxisSourceHostileControls(unittest.TestCase):
    def test_fixture_structural_only(self):
        self.assertEqual(check(fixture())["status"],"AXIS_MATRIX_STRUCTURAL_ONLY")

    def test_source_digest_falsifier(self):
        d=fixture();d["source_blend_sha256"]="0"*64
        with self.assertRaises(Rejected):check(d)

    def test_missing_axis_row(self):
        d=fixture();d["axis_probes"].pop()
        with self.assertRaises(Rejected):check(d)

    def test_duplicate_axis_instead_of_unique(self):
        d=fixture();d["axis_probes"][-1]=copy.deepcopy(d["axis_probes"][0])
        with self.assertRaises(Rejected):check(d)

    def test_forbid_false_foot_contact_and_promotion(self):
        for field,value in (("foot_contact","PASS"),("product_accepted",True),
                            ("real_world_sagittal_basis","CERTIFIED"),
                            ("signed_joint_coordinate_system","JCS_PASS")):
            d=fixture();d[field]=value
            with self.subTest(field=field),self.assertRaises(Rejected):check(d)

    def test_forbid_forged_zero_motion(self):
        d=fixture()
        for row in d["axis_probes"]:
            row["observed_displacement_m"]=0.
            row["observed_skinned_world_displacement_xyz"]=[0.,0.,0.]
        d["max_actual_weighted_foot_motion_m"]=0.
        with self.assertRaises(Rejected):check(d)

    def test_bad_sample_population(self):
        d=fixture();d["axis_probes"][0]["sampled_source_skin_vertices"]=0
        with self.assertRaises(Rejected):check(d)

    def test_nan_perturbed_vertex(self):
        d=fixture();d["axis_probes"][0]["perturbed_foot_region_world_xyz"][1]=float("nan")
        with self.assertRaises(Rejected):check(d)

    def test_mismatched_reported_geometry(self):
        d=fixture();d["axis_probes"][0]["observed_displacement_m"]=.5
        with self.assertRaises(Rejected):check(d)

    def test_wrong_bone_count_and_timebase(self):
        for field,value in (("fps",24),("frame",35)):
            d=fixture();d[field]=value
            with self.assertRaises(Rejected):check(d)
        d=fixture();d["rig_owners"][ROOTS[0]]["bone_count"]=79
        with self.assertRaises(Rejected):check(d)


if __name__=="__main__":
    unittest.main()
