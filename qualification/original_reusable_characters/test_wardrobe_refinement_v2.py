"""Adversarial qualification for additive R009 A1/A3/A5 candidate."""
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from modular_wardrobe_v1 import ACTORS, PRESETS
from test_modular_wardrobe_v1 import witness
from verify_original_glb import decode, accessory
from wardrobe_refinement_v2 import build
from wardrobe_portable_export_v2 import export

class RefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        cls.source=cls.root/"source.glb"
        cls.manifest=cls.root/"source.json"
        cls.receipt=build(cls.source,cls.manifest)
        cls.m=json.loads(cls.manifest.read_text())
        cls.d,cls.bb=decode(cls.source.read_bytes())
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_same_rig_and_slots_without_promotion(self):
        result=witness(self.source,self.manifest)
        self.assertEqual(result["joints_each"],35)
        self.assertFalse(result["human_visual_accepted"])
        self.assertTrue(self.m["separate_new_geometry_for_alternate"])
        self.assertTrue(self.receipt["contiguous_trunk_neck_head_loft"])
        self.assertFalse(self.receipt["full_body_watertight"])
        self.assertEqual(self.d["extras"]["wardrobe_contract"]["schema"],
                         "scp.original_wardrobe.v1")
        self.assertFalse(self.m["release_approved"])

    def test_alternate_is_new_geometry_not_a_material_only_clone(self):
        for actor in ACTORS:
            slots=self.m["actor_slots"][actor]
            for old,new in (("top","alt_top"),("bottom","alt_bottom")):
                sig=self.d["meshes"][slots[old]["mesh"]]["primitives"]
                alt=self.d["meshes"][slots[new]["mesh"]]["primitives"]
                self.assertNotEqual(sig,alt)
                self.assertNotEqual(
                    sum(self.d["accessors"][p["attributes"]["POSITION"]]["count"] for p in sig),
                    sum(self.d["accessors"][p["attributes"]["POSITION"]]["count"] for p in alt))
                for prim in alt:
                    positions=accessory(self.d,self.bb,prim["attributes"]["POSITION"])
                    self.assertTrue(all(math.isfinite(v) for xyz in positions for v in xyz))
            self.assertEqual(self.m["cut_styles"][actor]["alt_top"],
                             "cropped_sleeveless_vest_v2")
            self.assertEqual(self.m["cut_styles"][actor]["alt_bottom"],
                             "flared_calf_length_culottes_v2")

    def test_full_body_and_independent_portable_selection(self):
        for index, pair in enumerate((
            ("unclothed","unclothed"),("signature","alternate"),
            ("alternate","signature"),("alternate","alternate"))):
            choices=dict(zip(ACTORS,pair))
            glb=self.root/f"portable_{index}.glb"
            receipt=self.root/f"portable_{index}.json"
            result=export(self.source,self.manifest,glb,receipt,choices)
            d,bb=decode(glb.read_bytes())
            for actor in ACTORS:
                root=next(n for n in d["nodes"] if n["name"]==actor+"_SceneRoot")
                active={slot for slot,entry in self.m["actor_slots"][actor].items()
                        if entry["node"] in root["children"]}
                self.assertEqual(active,set(PRESETS[choices[actor]]) &
                                 set(self.m["actor_slots"][actor]))
                self.assertIn("body",active)
                self.assertEqual(active,set(result["active_layers"][actor]))
            self.assertTrue(result["source_geometry_preserved"])
            self.assertEqual(result["portable_export_contract"],
                             "scp.r009.original_wardrobe_portable_export.v2")
            self.assertEqual(d["skins"],self.d["skins"])
            self.assertEqual(d["animations"],self.d["animations"])
            self.assertEqual(d["meshes"],self.d["meshes"])
            for actor in ACTORS:
                slots=self.m["actor_slots"][actor]
                unwanted=set(slots)-set(PRESETS[choices[actor]])
                self.assertEqual(set(result["inactive_mesh_bindings_removed"][actor]),
                                 unwanted)
                for slot,entry in slots.items():
                    node=d["nodes"][entry["node"]]
                    if slot in unwanted:
                        self.assertNotIn("mesh",node,
                                         "Blender imports inactive orphan meshes")
                        self.assertNotIn("skin",node)
                    else:
                        self.assertIn("mesh",node)
                        self.assertIn("skin",node)

            self.assertEqual(hashlib.sha256(glb.read_bytes()).hexdigest(),
                             result["derived_sha256"])

    def test_portable_export_rejects_output_reuse_and_mutations(self):
        outputs=self.root/"first-v2.glb",self.root/"first-v2.json"
        selected={a:"unclothed" for a in ACTORS}
        original_sha=hashlib.sha256(self.source.read_bytes()).hexdigest()
        export(self.source,self.manifest,*outputs,selected)
        with self.assertRaisesRegex(FileExistsError,
                                    "REFUSE_OVERWRITE_EXISTING_PORTABLE_OUTPUT"):
            export(self.source,self.manifest,*outputs,selected)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),
                         original_sha)
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_RECEIPT_OVERWRITE_REFUSED"):
            export(self.source,self.manifest,self.source,self.root/"forbid.json",
                   selected)

    def test_output_immutability_and_manifest_falsifier(self):
        with self.assertRaisesRegex(ValueError,"IMMUTABLE_OUTPUT_EXISTS"):
            build(self.source,self.root/"changed-manifest.json")
        with self.assertRaisesRegex(ValueError,"OUTPUT_PATH_COLLISION"):
            build(self.root/"same.glb",self.root/"same.glb")
        fake=json.loads(self.manifest.read_text())
        fake["derived_sha256"]="0"*64
        bad=self.root/"bad_manifest.json"
        bad.write_text(json.dumps(fake))
        with self.assertRaisesRegex(ValueError,"SOURCE_MANIFEST_SHA_MISMATCH"):
            export(self.source,bad,self.root/"forged.glb",
                   self.root/"forged.json",{a:"signature" for a in ACTORS})

if __name__=="__main__":unittest.main()
