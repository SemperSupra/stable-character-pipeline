"""Independent hostile tests for MIT source-labeled UV material assignment; no Blender runtime required."""
import unittest
from native_material_uv import classify_source_material, validate_material_plan, SCHEMA, TEXTURES


def row(kind, polygons=10, uv=True, name="source"):
    return {"classification": kind, "polygons": polygons, "uv_present": uv, "material": name}


class OriginalMaterialTest(unittest.TestCase):
    def test_source_material_head(self):
        self.assertEqual(classify_source_material("f001_head", []), "head")

    def test_source_material_body(self):
        self.assertEqual(classify_source_material("F02_Body", []), "body")

    def test_native_image_label_resolution(self):
        self.assertEqual(classify_source_material("Material_002", ["f001_head_color.tga"]), "head")

    def test_unknown_unlabeled_source(self):
        self.assertEqual(classify_source_material("Material.002", []), "UNKNOWN")

    def test_reject_conflicting_identity_source(self):
        self.assertEqual(classify_source_material("body_head", ["body_diffuse.tga"]), "UNKNOWN")

    def test_never_infer_body_from_word_substring(self):
        self.assertEqual(classify_source_material("anyBODY", []), "UNKNOWN")

    def test_never_infer_face_from_surface(self):
        self.assertEqual(classify_source_material("surface", []), "UNKNOWN")

    def test_complete_both_coverage(self):
        self.assertEqual(validate_material_plan([row("body", 250), row("head", 75)]),
                         {"body": 250, "head": 75})

    def test_missing_head_forbidden(self):
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_BODY_HEAD"):
            validate_material_plan([row("body", 100)])

    def test_missing_native_uv_forbidden(self):
        with self.assertRaisesRegex(ValueError, "MISSING_NATIVE_UV"):
            validate_material_plan([row("body", 250, uv=False), row("head", 75)])

    def test_unknown_active_material_forbidden(self):
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_MATERIAL_WITH_POLYGONS"):
            validate_material_plan([row("body"), row("head"), row("UNKNOWN", 30)])

    def test_irrelevant_unassigned_zero_polygon_unknown_allowed(self):
        self.assertEqual(validate_material_plan([row("body"), row("head"), row("UNKNOWN", 0)]),
                         {"body": 10, "head": 10})

    def test_nonfinite_or_boolean_counts_forbidden(self):
        for n in (True, -1, 1.5, float("nan"), None):
            with self.subTest(n=n), self.assertRaises(ValueError):
                validate_material_plan([row("body", n), row("head")])

    def test_immutable_source_manifest(self):
        self.assertEqual(len(TEXTURES), 2)
        self.assertEqual(set(TEXTURES["RB_RB_F01_root"]), {"body", "head"})
        self.assertTrue(SCHEMA.endswith(".v1"))


if __name__ == "__main__":
    unittest.main()
