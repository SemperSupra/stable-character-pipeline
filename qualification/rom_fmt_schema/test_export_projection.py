import json
import pathlib
import unittest
import xml.etree.ElementTree as ET
from export_projection import fixture,inspect_source_projection,usd_fragment,urdf,mjcf,opensim_coordinate

class FormatSemantics(unittest.TestCase):
    def test_eight_format_capability_matrix_references(self):
        data=json.loads(pathlib.Path(__file__).with_name("format_matrix.json").read_text())
        self.assertEqual(data["schema"],"scp.rom.format_capability_matrix.v1")
        self.assertEqual(len(data["formats"]),8)
        self.assertEqual({x["id"] for x in data["formats"]},{"blend","usd","fbx","gltf","osim","urdf","mjcf","vtk"})
        self.assertTrue(all(x["reference"].startswith("https://") and x["semantic"] for x in data["formats"]))
        self.assertEqual(data["default_if_lost"],"FAIL_METADATA_PRESERVATION_NOT_UNLIMITED_ROM")
    def test_cross_format_source_projection_no_native_promotion(self):
        m=fixture();r=inspect_source_projection(m)
        self.assertEqual(r["status"],"SOURCE_TEXT_PROJECTION_TEST_ONLY_NOT_NATIVE_ENGINE")
        self.assertEqual(r["source_position_bounds_rad"],[-1.,1.])
        self.assertEqual(r["angles_by_format"]["USD"],"degrees")
        self.assertIn("EFFORT_UNMODELED",r["survival"]["MJCF"])
        self.assertIn("native_file_parser",r["unverified"])
        self.assertIn("physics_vs_usdskel",r["unverified"])
    def test_usd_radians_are_converted_to_degrees(self):
        content=usd_fragment(fixture())
        self.assertIn('physics:lowerLimit = -57.2957795131',content)
        self.assertIn('physics:upperLimit = 57.2957795131',content)
        self.assertIn('metersPerUnit = 1',content)
    def test_urdf_velocity_and_effort_source_fields_not_dropped(self):
        joint=ET.fromstring(urdf(fixture())).find("./joint")
        self.assertEqual(joint.find("limit").get("velocity"),"2.0")
        self.assertEqual(joint.find("limit").get("effort"),"10.0")
    def test_mjcf_angle_explicit_and_no_fake_actuator(self):
        doc=ET.fromstring(mjcf(fixture()))
        self.assertEqual(doc.find("compiler").get("angle"),"radian")
        self.assertIsNone(doc.find("actuator"))
    def test_opensim_fragment_is_clamped_not_complete(self):
        doc=ET.fromstring(opensim_coordinate(fixture()))
        self.assertEqual(doc.tag,"Coordinate")
        self.assertEqual(doc.findtext("clamped"),"true")
        self.assertEqual(doc.findtext("range"),"-1.0 1.0")
    def test_no_unapproved_human_limits(self):
        m=fixture();m["authority"]="HUMAN_ANATOMICAL_CLAIM"
        with self.assertRaisesRegex(ValueError,"RIGHTS_OR_LIMIT_AUTHORITY"):
            inspect_source_projection(m)
    def test_axis_mismatch_rejected_not_flipped(self):
        m=fixture();m["axis"]=[-1,0,0]
        with self.assertRaisesRegex(ValueError,"AXIS_NOT_USD_CARDINAL"):
            inspect_source_projection(m)
    def test_no_fake_effort_or_velocity(self):
        for key in ("max_velocity","max_effort"):
            m=fixture();m.pop(key)
            with self.assertRaisesRegex(ValueError,"NUMERIC_LIMIT_INVALID"):
                inspect_source_projection(m)
    def test_bad_ranges_and_frame_refused(self):
        m=fixture();m["hard_min"]=2
        with self.assertRaisesRegex(ValueError,"LIMITS_INVALID"):
            inspect_source_projection(m)
        m=fixture();m["unit"]="deg"
        with self.assertRaisesRegex(ValueError,"JOINT_KIND_UNIT_OR_FRAME"):
            inspect_source_projection(m)
        m=fixture();m["frame"]="WORLD"
        with self.assertRaisesRegex(ValueError,"JOINT_KIND_UNIT_OR_FRAME"):
            inspect_source_projection(m)
if __name__=="__main__":
    unittest.main()
