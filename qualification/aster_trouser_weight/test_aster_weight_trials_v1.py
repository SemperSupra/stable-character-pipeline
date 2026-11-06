#!/usr/bin/env python3
"""Aster source-original only 35j trouser skin-weight adversarial tests."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"original_reusable_characters"))
from modular_wardrobe_v1 import ACTORS,build
from parametric_morphology_v1 import apply as morph
from original_mage_outfits_v1 import add_original_outfits
from strict_mage_portable_v1 import export as strict
from verify_original_glb import accessory,decode
from aster_weight_trials_v1 import apply,OPTIONS,SCHEMA,influenced,pt_on_bone

class AsterWeightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        r=cls.root=Path(cls.temp.name)
        build(r/"original.glb",r/"original.json")
        morph(r/"original.glb",r/"original.json",
              r/"morph.glb",r/"morph.json",r/"morph-receipt.json")
        add_original_outfits(r/"morph.glb",r/"morph.json",
                             r/"author.glb",r/"author.json",r/"author-receipt.json")
        strict(r/"author.glb",r/"author.json",
               r/"base.glb",r/"base-receipt.json",
               {actor:"adventure" for actor in ACTORS})
        cls.source=(r/"base.glb").read_bytes()
        cls.sha=hashlib.sha256(cls.source).hexdigest()
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def trial(self,variant,name):
        r=self.root
        glb,rec=r/(name+".glb"),r/(name+".json")
        result=apply(r/"base.glb",r/"base-receipt.json",glb,rec,variant)
        self.assertEqual(result["schema"],SCHEMA+".receipt")
        self.assertEqual(result["source_sha256"],self.sha)
        self.assertEqual(result["derived_sha256"],hashlib.sha256(glb.read_bytes()).hexdigest())
        self.assertFalse(result["garment_clearance_accepted"])
        self.assertEqual((r/"base.glb").read_bytes(),self.source)
        return glb,result

    def test_all_weight_candidates_source_actors_and_animation_immutable(self):
        original,binary=decode(self.source)
        names={node["name"]:i for i,node in enumerate(original["nodes"])}
        actor="AsterOriginal"
        target_node=original["nodes"][names[actor+"_Wardrobe_style_bottom"]]
        target_mesh=target_node["mesh"]
        for variant in OPTIONS:
            with self.subTest(variant=variant):
                path,r=self.trial(variant,"regular-"+variant)
                after,changed=decode(path.read_bytes())
                self.assertEqual(original["nodes"],after["nodes"])
                self.assertEqual(original["skins"],after["skins"])
                self.assertEqual(original["animations"],after["animations"])
                self.assertEqual(original["meshes"],after["meshes"])
                self.assertEqual(original["materials"],after["materials"])
                self.assertEqual(original["accessors"],after["accessors"])
                self.assertEqual(original["bufferViews"],after["bufferViews"])
                self.assertEqual(r["actor"],actor)
                for idx,mesh in enumerate(original["meshes"]):
                    for primitive in mesh["primitives"]:
                        attrs=primitive["attributes"]
                        for semantic in ("POSITION","NORMAL","JOINTS_0","WEIGHTS_0"):
                            attr=attrs[semantic]
                            x=accessory(original,binary,attr)
                            y=accessory(after,changed,attr)
                            if idx==target_mesh and semantic=="WEIGHTS_0":
                                self.assertEqual(len(x),len(y))
                            else:
                                self.assertEqual(x,y,variant+":"+semantic)
                counts=r["counts"]
                if variant.startswith("hip") or variant.startswith("combo"):
                    self.assertGreater(counts["hip_reblend"],100)
                if variant.startswith("hem") or variant.startswith("combo"):
                    self.assertGreater(counts["hem_ankle_reduced"],40)
                if variant=="hem_30":
                    self.assertEqual(counts["hip_reblend"],0)
                if variant=="hip_linear":
                    self.assertEqual(counts["hem_ankle_reduced"],0)

    def test_deterministic_exact_bytes(self):
        a,x=self.trial("combo_hem30_linear","det-a")
        b,y=self.trial("combo_hem30_linear","det-b")
        self.assertEqual(a.read_bytes(),b.read_bytes())
        self.assertEqual(x["derived_sha256"],y["derived_sha256"])

    def test_reject_input_alias(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_OVERWRITE"):
            apply(self.root/"base.glb",self.root/"base-receipt.json",
                  self.root/"base.glb",self.root/"bad1.json","hem_30")

    def test_reject_existing_destination(self):
        path,rec=self.trial("hem_30","already")
        with self.assertRaisesRegex(FileExistsError,"OUTPUT_EXISTS"):
            apply(self.root/"base.glb",self.root/"base-receipt.json",
                  path,self.root/"already.json","hem_30")

    def test_reject_mismatched_receipt_hash(self):
        old=json.loads((self.root/"base-receipt.json").read_text())
        old["derived_sha256"]="f"*64
        meta=self.root/"tamper.json"
        meta.write_text(json.dumps(old))
        with self.assertRaisesRegex(ValueError,"SOURCE_RECEIPT_MISMATCH"):
            apply(self.root/"base.glb",meta,self.root/"bad2.glb",
                  self.root/"bad2.json","hem_50")

    def test_reject_variant_and_bad_axes(self):
        with self.assertRaisesRegex(ValueError,"VARIANT_UNKNOWN"):
            apply(self.root/"base.glb",self.root/"base-receipt.json",
                  self.root/"bad3.glb",self.root/"bad3.json","magic")
        with self.assertRaisesRegex(ValueError,"BONE_AXIS_INVALID"):
            pt_on_bone((0.,0.,0.),(0.,0.,0.),(0.,0.,0.))

    def test_weight_mutation_scientific_boundary(self):
        names={5:"hip_L",6:"knee_L",7:"ankle_L"}
        v,category=influenced((1.,0.,0.,0.),(5,6,0,0),
                (-.13,.89,0),names,"linear",1.)
        self.assertEqual(category,"hip_reblend")
        self.assertAlmostEqual(v[0],1.)
        v2,category2=influenced((0.,1.,0.,0.),(6,7,0,0),
                (-.14,.36,0),names,"baseline",.30)
        self.assertEqual(category2,"hem_ankle_reduced")
        self.assertAlmostEqual(v2[1],.30)
        self.assertAlmostEqual(sum(v2),1.)
        self.assertEqual(influenced((1.,0.,0.,0.),(0,1,0,0),
                         (0.,1.2,0.),names,"linear",.3)[1],"non_leg")

if __name__=="__main__":unittest.main()
