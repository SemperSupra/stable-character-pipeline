"""Independent original new-cut garment tests; no imported series media."""
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from modular_wardrobe_v1 import ACTORS, build
from original_mage_outfits_v1 import (
    ADVENTURE, SCHEMA, add_original_outfits, export_adventure)
from parametric_morphology_v1 import apply
from verify_original_glb import accessory, decode


class OriginalOutfitsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        cls.original=cls.root/"original.glb"
        cls.base_manifest=cls.root/"base.json"
        build(cls.original, cls.base_manifest)
        cls.morph=cls.root/"morph.glb"
        cls.morph_manifest=cls.root/"morph.json"
        apply(cls.original, cls.base_manifest, cls.morph, cls.morph_manifest,
              cls.root/"morph_receipt.json")
        cls.out=cls.root/"outfit.glb"
        cls.manifest=cls.root/"outfit.json"
        cls.proof=add_original_outfits(
            cls.morph, cls.morph_manifest, cls.out, cls.manifest,
            cls.root/"outfit_receipt.json")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_source_untouched_and_rig_animation_preserved(self):
        before, _=decode(self.morph.read_bytes())
        after, _=decode(self.out.read_bytes())
        self.assertEqual(before["skins"],after["skins"])
        self.assertEqual(before["animations"],after["animations"])
        self.assertEqual(len(after["skins"]),2)
        self.assertEqual([len(s["joints"]) for s in after["skins"]],[35,35])
        self.assertEqual(self.proof["source_sha256"],
                         hashlib.sha256(self.morph.read_bytes()).hexdigest())
        self.assertEqual(self.proof["derived_sha256"],
                         hashlib.sha256(self.out.read_bytes()).hexdigest())
        self.assertEqual(after["extras"]["original_mage_outfits"]["schema"],SCHEMA)
        self.assertFalse(self.proof["garment_collision_accepted"])
        self.assertFalse(self.proof["human_visual_accepted"])

    def test_new_cut_is_real_geometry_and_distinct_from_recolors(self):
        doc, bb=decode(self.out.read_bytes())
        m=json.loads(self.manifest.read_text())
        self.assertEqual(m["presets"]["adventure"],list(ADVENTURE))
        self.assertTrue(m["separate_new_geometry_for_adventure"])
        for i,actor in enumerate(ACTORS):
            slots=m["actor_slots"][actor]
            for slot in ("style_top","style_bottom"):
                new=slots[slot]; old=slots["top" if slot=="style_top" else "bottom"]
                self.assertNotEqual(new["mesh"],old["mesh"])
                node=doc["nodes"][new["node"]]
                self.assertEqual(node["skin"],i)
                self.assertEqual(new["skin"],i)
                mesh=doc["meshes"][new["mesh"]]
                self.assertTrue(mesh["name"].endswith("_NEW_CUT"))
                self.assertTrue(mesh["primitives"])
                original_accessors={
                    p["attributes"]["POSITION"]
                    for p in doc["meshes"][old["mesh"]]["primitives"]}
                for p in mesh["primitives"]:
                    a=p["attributes"]
                    self.assertNotIn(a["POSITION"],original_accessors)
                    points=accessory(doc,bb,a["POSITION"])
                    joints=accessory(doc,bb,a["JOINTS_0"])
                    weights=accessory(doc,bb,a["WEIGHTS_0"])
                    self.assertGreater(len(points),40)
                    self.assertEqual(len(points),len(joints))
                    self.assertEqual(len(points),len(weights))
                    self.assertTrue(all(all(math.isfinite(v) for v in xyz) for xyz in points))
                    self.assertTrue(all(all(j < 35 for j in joint) for joint in joints))
                    self.assertTrue(all(abs(sum(w)-1.) < 1.e-5 for w in weights))
            self.assertGreater(self.proof["garment_vertex_counts"][actor]["style_top"],150)
            self.assertGreater(self.proof["garment_vertex_counts"][actor]["style_bottom"],150)

    def test_female_skirt_hem_and_male_vest_are_different_shapes(self):
        doc, bb=decode(self.out.read_bytes())
        m=json.loads(self.manifest.read_text())
        def coords(actor,slot):
            mesh=doc["meshes"][m["actor_slots"][actor][slot]["mesh"]]
            return [pos for prim in mesh["primitives"]
                    for pos in accessory(doc,bb,prim["attributes"]["POSITION"])]
        male_top=coords("AsterOriginal","style_top")
        male_bottom=coords("AsterOriginal","style_bottom")
        female_bottom=coords("JuniperOriginal","style_bottom")
        self.assertGreater(min(p[1] for p in male_top),1.01)  # sleeveless vest
        self.assertGreater(max(p[1] for p in male_top),1.41)
        self.assertLess(min(p[1] for p in male_bottom),.45)    # cropped pants
        self.assertLess(min(p[1] for p in female_bottom),.58)  # skirt hem
        skirt_hem=[abs(p[0]) for p in female_bottom if p[1] < .60]
        skirt_waist=[abs(p[0]) for p in female_bottom if p[1] > 1.02]
        self.assertGreater(max(skirt_hem),max(skirt_waist)*1.3)

    def test_portable_mixed_choice_cloth_and_body_are_selectable(self):
        out=self.root/"worn.glb"; receipt=self.root/"worn.json"
        r=export_adventure(self.out,self.manifest,out,receipt,{
            "AsterOriginal":"adventure","JuniperOriginal":"signature"})
        self.assertIn("style_top",r["active_layers"]["AsterOriginal"])
        self.assertIn("style_bottom",r["active_layers"]["AsterOriginal"])
        self.assertNotIn("top",r["active_layers"]["AsterOriginal"])
        self.assertIn("top",r["active_layers"]["JuniperOriginal"])
        self.assertNotIn("style_top",r["active_layers"]["JuniperOriginal"])
        self.assertTrue(all("body" in r["active_layers"][actor] for actor in ACTORS))
        doc,_=decode(out.read_bytes())
        self.assertEqual(len(doc["animations"][0]["channels"]),
                         len(decode(self.out.read_bytes())[0]["animations"][0]["channels"]))

    def test_tamper_and_overwrite_refused(self):
        m=json.loads(self.morph_manifest.read_text())
        m["derived_sha256"]="0"*64
        altered=self.root/"tampered.json";altered.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,"OUTFIT_SOURCE_MANIFEST_SHA"):
            add_original_outfits(self.morph,altered,self.root/"wrong.glb",
                                 self.root/"wrong.json",self.root/"wrong_receipt.json")
        with self.assertRaisesRegex(ValueError,"OUTFIT_SOURCE_OVERWRITE"):
            add_original_outfits(self.morph,self.morph_manifest,self.morph,
                                 self.root/"wrong.json",self.root/"wrong_receipt.json")
        with self.assertRaisesRegex(ValueError,"ADVENTURE_UNKNOWN_PRESET"):
            export_adventure(self.out,self.manifest,self.root/"bad.glb",
                             self.root/"bad.json",{"AsterOriginal":"fake",
                                                   "JuniperOriginal":"adventure"})

    def test_deterministic_generation(self):
        other=self.root/"repeat.glb"
        r=add_original_outfits(self.morph,self.morph_manifest,other,
                               self.root/"repeat.json",self.root/"repeat_receipt.json")
        self.assertEqual(r["derived_sha256"],self.proof["derived_sha256"])
        self.assertEqual(other.read_bytes(),self.out.read_bytes())


if __name__=="__main__":
    unittest.main()
