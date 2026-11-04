"""Independent hostile controls for original MIT 3-slot native material identity and UV binding."""
import unittest
from native_material_uv import classify_source_material, validate_material_plan, SCHEMA, TEXTURES, SOURCE_TGA_BYTES


def row(kind, polygons=10, uv=True, name="source"):
    return {"classification": kind, "polygons": polygons, "uv_present": uv, "material": name}


class OriginalMaterialTest(unittest.TestCase):
    def test_source_material_head(self):
        self.assertEqual(classify_source_material("f001_head", []), "head")

    def test_source_material_body(self):
        self.assertEqual(classify_source_material("F02_Body", []), "body")

    def test_native_image_label_resolution(self):
        self.assertEqual(classify_source_material("Material_002", ["f001_head_color.tga"]), "head")

    def test_source_opacity_material(self):
        self.assertEqual(classify_source_material("f001_opacity", ["f001_opacity_color.tga"]), "opacity")

    def test_opacity_exact_token_not_substring(self):
        self.assertEqual(classify_source_material("overopacitymask", []), "UNKNOWN")

    def test_opacity_ambiguous_head_label_rejected(self):
        self.assertEqual(classify_source_material("f001_opacity", ["f001_head_color.tga"]), "UNKNOWN")

    def test_unknown_unlabeled_source(self):
        self.assertEqual(classify_source_material("Material.002", []), "UNKNOWN")

    def test_reject_conflicting_identity_source(self):
        self.assertEqual(classify_source_material("body_head", ["body_diffuse.tga"]), "UNKNOWN")

    def test_never_infer_body_from_word_substring(self):
        self.assertEqual(classify_source_material("anyBODY", []), "UNKNOWN")

    def test_never_infer_face_from_surface(self):
        self.assertEqual(classify_source_material("surface", []), "UNKNOWN")

    def test_complete_three_slot_coverage(self):
        self.assertEqual(validate_material_plan([row("body", 250), row("head", 75), row("opacity", 42)]),
                         {"body": 250, "head": 75, "opacity": 42})

    def test_missing_head_forbidden(self):
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_BODY_HEAD_OPACITY"):
            validate_material_plan([row("body", 100), row("opacity", 2)])

    def test_missing_opacity_forbidden(self):
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_BODY_HEAD_OPACITY"):
            validate_material_plan([row("body"), row("head")])

    def test_missing_native_uv_forbidden(self):
        with self.assertRaisesRegex(ValueError, "MISSING_NATIVE_UV"):
            validate_material_plan([row("body", 250, uv=False), row("head", 75), row("opacity", 12)])

    def test_unknown_active_material_forbidden(self):
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_MATERIAL_WITH_POLYGONS"):
            validate_material_plan([row("body"), row("head"), row("opacity"), row("UNKNOWN", 30)])

    def test_irrelevant_unassigned_unknown_allowed(self):
        self.assertEqual(validate_material_plan([row("body"), row("head"), row("opacity"), row("UNKNOWN", 0)]),
                         {"body": 10, "head": 10, "opacity": 10})

    def test_nonfinite_or_boolean_counts_forbidden(self):
        for n in (True, -1, 1.5, float("nan"), None):
            with self.subTest(n=n), self.assertRaises(ValueError):
                validate_material_plan([row("body", n), row("head"), row("opacity")])

    def test_immutable_source_manifest(self):
        self.assertEqual(len(TEXTURES), 2)
        self.assertEqual(set(TEXTURES["RB_RB_F01_root"]), {"body", "head", "opacity"})
        self.assertEqual(len(SOURCE_TGA_BYTES), 6)
        self.assertEqual(SOURCE_TGA_BYTES["f001_opacity_color.tga"], 16777260)
        self.assertEqual(SOURCE_TGA_BYTES["f002_opacity_color.tga"], 4194348)
        self.assertTrue(SCHEMA.endswith(".v1"))


    def test_original_fbx_parent_directory_opacity_does_not_label_body(self):
        self.assertEqual(classify_source_material(
            "f001_body",
            ["//../rocket/D:/temp/Humans/with_opacity_version/f001/textures/f001_body_color.tga"]
        ), "body")

    def test_original_fbx_parent_directory_opacity_does_not_label_head(self):
        self.assertEqual(classify_source_material(
            "f001_head",
            ["//../rocket/D:/temp/Humans/with_opacity_version/f001/textures/f001_head_color.tga"]
        ), "head")

    def test_original_material_and_image_basename_conflict_rejected(self):
        self.assertEqual(classify_source_material(
            "f001_body",
            ["//../rocket/D:/temp/Humans/with_opacity_version/f001/textures/f001_head_color.tga"]
        ), "UNKNOWN")

    def test_windows_path_basename_normalized(self):
        self.assertEqual(classify_source_material(
            "f002_body",
            ["D:\\Humans\\with_opacity_version\\f002\\textures\\f002_body_color.tga"]
        ), "body")


if __name__ == "__main__":
    unittest.main()
