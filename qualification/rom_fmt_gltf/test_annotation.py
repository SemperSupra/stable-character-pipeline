import copy
import unittest
from annotation import add_extras,verify,to_glb,from_glb,canonical,digest

def sample():
    source={"schema":"scp.rom.joint_annotation.v1",
            "rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "authority":"SYNTHETIC_TEST_ONLY","rig_id":"original-actor-001",
            "joints":[{"id":"left-hinge","node":"LeftLower","parent":"LeftUpper",
                       "kind":"revolute","unit":"rad","axis":[1.0,0.0,0.0],
                       "frame":"PARENT_LOCAL_TEST_ONLY","hard_min":-1.0,"hard_max":1.0,
                       "provenance":"SYNTHETIC_TEST_ONLY"}]}
    gltf={"asset":{"version":"2.0"},"nodes":[{"name":"Root","children":[1]},
                 {"name":"LeftUpper","children":[2]},{"name":"LeftLower"}],
          "skins":[{"joints":[1,2],"skeleton":1}],"scenes":[{"nodes":[0]}],"scene":0}
    return source,gltf

class Roundtrip(unittest.TestCase):
    def test_native_glb_roundtrip_and_explicit_non_enforcement(self):
        m,a=sample();add_extras(a,m)
        binary=to_glb(a)
        recovered=from_glb(binary)
        receipt=verify(recovered,m)
        self.assertEqual(receipt["status"],"PASS_METADATA_PRESERVED_TEST_ONLY")
        self.assertEqual(receipt["enforcement"],"NOT_GUARANTEED_BY_GLTF")
        self.assertEqual(receipt["manifest_sha256"],digest(canonical(m)))
        self.assertEqual(receipt["joints_checked"],1)
    def test_removed_metadata_fail_closed(self):
        m,a=sample();add_extras(a,m)
        del a["nodes"][2]["extras"]
        with self.assertRaisesRegex(ValueError,"EXTRAS_MISSING"):
            verify(a,m)
    def test_altered_joint_limits_fail_closed(self):
        m,a=sample();add_extras(a,m)
        a["nodes"][2]["extras"]["scp_rom_v1"]["hard_max"]=2.0
        with self.assertRaisesRegex(ValueError,"EXTRAS_MISSING"):
            verify(a,m)
    def test_changed_authority_has_new_hash_and_abstain(self):
        m,a=sample();add_extras(a,m)
        m["joints"][0]["hard_max"]=.5
        with self.assertRaisesRegex(ValueError,"EXTRAS_MISSING"):
            verify(a,m)
    def test_renamed_or_wrong_skin_joint(self):
        m,a=sample();add_extras(a,m)
        a["skins"][0]["joints"]=[1]
        with self.assertRaisesRegex(ValueError,"JOINT_NODE_NOT_UNIQUE_SKIN"):
            verify(a,m)
    def test_no_unapproved_human_anatomy_values(self):
        m,a=sample();m["authority"]="HUMAN_CLINICAL_UNVERIFIED"
        with self.assertRaisesRegex(ValueError,"AUTHORITY_RIGHTS_OR_SCHEMA"):
            add_extras(a,m)
    def test_duplicate_skin_node_name_rejected(self):
        m,a=sample();a["nodes"][0]["name"]="LeftLower"
        with self.assertRaisesRegex(ValueError,"JOINT_NODE_NOT_UNIQUE_SKIN"):
            add_extras(a,m)
    def test_invalid_axis_rejected(self):
        m,a=sample();m["joints"][0]["axis"]=[2,0,0]
        with self.assertRaisesRegex(ValueError,"AXIS_UNIT_LENGTH"):
            add_extras(a,m)
    def test_corrupt_glb_length_version_chunk(self):
        m,a=sample();add_extras(a,m);data=bytearray(to_glb(a))
        for idx,value,expected in [(4,1,"GLB_VERSION_LENGTH"),(8,1,"GLB_VERSION_LENGTH"),(16,1,"GLB_JSON_CHUNK_INVALID")]:
            b=bytearray(data);b[idx]=value
            with self.assertRaisesRegex(ValueError,expected):
                from_glb(bytes(b))
    def test_same_metadata_not_authoritative_enforcement(self):
        m,a=sample();add_extras(a,m)
        self.assertIn("scp_rom_v1",a["nodes"][2]["extras"])
        self.assertEqual(verify(a,m)["anatomy"],"UNKNOWN_NOT_MEASURED")
if __name__=="__main__":
    unittest.main()
