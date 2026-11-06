"""Hostile strict portable Blender import predictor for male/female new cuts."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from modular_wardrobe_v1 import ACTORS, build
from original_mage_outfits_v1 import add_original_outfits, VALID_PRESETS
from parametric_morphology_v1 import apply
from strict_mage_portable_v1 import export, SCHEMA
from verify_original_glb import decode


class StrictPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        src=cls.root/"source.glb"
        manifest=cls.root/"source.json"
        build(src,manifest)
        morph=cls.root/"morph.glb"
        mm=cls.root/"morph.json"
        apply(src,manifest,morph,mm,cls.root/"morph-receipt.json")
        cls.authoring=cls.root/"authoring.glb"
        cls.authoring_manifest=cls.root/"authoring.json"
        add_original_outfits(morph,mm,cls.authoring,
                             cls.authoring_manifest,cls.root/"authoring-receipt.json")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def witness(self, label, presets):
        output=self.root/(label+".glb")
        receipt=self.root/(label+".json")
        result=export(self.authoring,self.authoring_manifest,output,receipt,presets)
        doc,_=decode(output.read_bytes())
        src,_=decode(self.authoring.read_bytes())
        manifest=json.loads(self.authoring_manifest.read_text())
        self.assertEqual(doc["animations"],src["animations"])
        self.assertEqual(doc["skins"],src["skins"])
        self.assertEqual(doc["meshes"],src["meshes"])
        self.assertEqual(doc["accessors"],src["accessors"])
        self.assertEqual(len(doc["skins"]),2)
        self.assertEqual([len(s["joints"]) for s in doc["skins"]],[35,35])
        self.assertEqual(result["schema"],SCHEMA+".receipt")
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),
                         result["derived_sha256"])
        for actor in ACTORS:
            root=next(n for n in doc["nodes"] if n["name"]==actor+"_SceneRoot")
            active=set(result["active_layers"][actor])
            expected=set(VALID_PRESETS[presets[actor]]) & set(manifest["actor_slots"][actor])
            self.assertEqual(active,expected)
            for slot, meta in manifest["actor_slots"][actor].items():
                node=doc["nodes"][meta["node"]]
                if slot in expected:
                    self.assertIn(meta["node"],root["children"])
                    self.assertEqual(node["mesh"],meta["mesh"])
                    self.assertEqual(node["skin"],meta["skin"])
                else:
                    self.assertNotIn(meta["node"],root["children"])
                    self.assertNotIn("mesh",node)
                    self.assertNotIn("skin",node)
        self.assertFalse(result["visual_accepted"])
        self.assertFalse(result["blender_import_accepted"])
        return result

    def test_adventure_adventure(self):
        self.witness("both-adventure", {a:"adventure" for a in ACTORS})

    def test_signature_and_unclothed(self):
        self.witness("mixed-legacy", {
            "AsterOriginal":"signature","JuniperOriginal":"unclothed"})

    def test_new_cuts_and_alt_color_compatibility(self):
        self.witness("mixed-mage-alt", {
            "AsterOriginal":"alternate","JuniperOriginal":"adventure"})

    def test_refuse_existing_output_and_source_alias(self):
        with self.assertRaisesRegex(ValueError,"STRICT_SOURCE_OR_RECEIPT_OVERWRITE"):
            export(self.authoring,self.authoring_manifest,self.authoring,
                   self.root/"unwritten.json",
                   {a:"adventure" for a in ACTORS})
        self.witness("overwrite-once", {a:"adventure" for a in ACTORS})
        with self.assertRaisesRegex(FileExistsError,"STRICT_REFUSE_OVERWRITE"):
            export(self.authoring,self.authoring_manifest,
                   self.root/"overwrite-once.glb",
                   self.root/"overwrite-once.json",
                   {a:"adventure" for a in ACTORS})

    def test_refuse_tampered_or_missing_manifest(self):
        meta=json.loads(self.authoring_manifest.read_text())
        meta["derived_sha256"]="0"*64
        forged=self.root/"tampered-manifest.json"
        forged.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError,"STRICT_SOURCE_MANIFEST_SHA"):
            export(self.authoring,forged,self.root/"tampered-out.glb",
                   self.root/"tampered-out.json",
                   {a:"adventure" for a in ACTORS})

    def test_refuse_invalid_preset_or_actor(self):
        invalid=[
            {"AsterOriginal":"fake","JuniperOriginal":"adventure"},
            {"AsterOriginal":"adventure","OtherOriginal":"signature"},
            {"AsterOriginal":"adventure"},
        ]
        for choices in invalid:
            with self.assertRaisesRegex(ValueError,"STRICT_UNKNOWN_ACTOR_OR_PRESET"):
                export(self.authoring,self.authoring_manifest,
                       self.root/"refused.glb",self.root/"refused.json",choices)

    def test_deterministic_export(self):
        p={a:"adventure" for a in ACTORS}
        a=export(self.authoring,self.authoring_manifest,self.root/"detA.glb",
                 self.root/"detA.json",p)
        b=export(self.authoring,self.authoring_manifest,self.root/"detB.glb",
                 self.root/"detB.json",p)
        self.assertEqual(a["derived_sha256"],b["derived_sha256"])
        self.assertEqual((self.root/"detA.glb").read_bytes(),
                         (self.root/"detB.glb").read_bytes())


if __name__ == "__main__":
    unittest.main()
