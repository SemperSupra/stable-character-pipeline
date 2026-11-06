#!/usr/bin/env python3
"""Adversarial source-original costume radius ablation regression checks."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
ORIGINAL=HERE.parent/"original_reusable_characters"
sys.path.insert(0,str(ORIGINAL))
from modular_wardrobe_v1 import ACTORS,build
from parametric_morphology_v1 import apply as morph
from original_mage_outfits_v1 import add_original_outfits
from strict_mage_portable_v1 import export as strict
from verify_original_glb import decode,accessory
from fit_radial_ablations_v1 import apply, CANDIDATES, SCHEMA, factors_for

class RadiusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        r=cls.root
        build(r/"base.glb",r/"base.json")
        morph(r/"base.glb",r/"base.json",
              r/"morph.glb",r/"morph.json",r/"morph-receipt.json")
        add_original_outfits(r/"morph.glb",r/"morph.json",
                             r/"author.glb",r/"author.json",r/"author-receipt.json")
        strict(r/"author.glb",r/"author.json",
               r/"source.glb",r/"source.json",{actor:"adventure" for actor in ACTORS})
        cls.original=(r/"source.glb").read_bytes()
        cls.original_sha=hashlib.sha256(cls.original).hexdigest()
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def execute(self,variant,tag):
        r=self.root
        out=r/(tag+".glb")
        rec=r/(tag+".json")
        receipt=apply(r/"source.glb",r/"source.json",out,rec,variant)
        self.assertEqual(receipt["schema"],SCHEMA+".receipt")
        self.assertEqual(receipt["source_sha256"],self.original_sha)
        self.assertEqual(receipt["derived_sha256"],
                         hashlib.sha256(out.read_bytes()).hexdigest())
        self.assertFalse(receipt["garment_clearance_accepted"])
        self.assertFalse(receipt["realistic_morphology_accepted"])
        self.assertEqual((r/"source.glb").read_bytes(),self.original)
        return out,receipt

    def test_all_four_source_original_variants_preserve_non_wardrobe(self):
        before,source_bin=decode(self.original)
        names={n["name"]:i for i,n in enumerate(before["nodes"])}
        for variant in CANDIDATES:
            with self.subTest(variant=variant):
                output,rec=self.execute(variant,"case-"+variant)
                after,new_bin=decode(output.read_bytes())
                self.assertEqual(before["skins"],after["skins"])
                self.assertEqual(before["animations"],after["animations"])
                self.assertEqual(before["nodes"],after["nodes"])
                self.assertEqual(before["materials"],after["materials"])
                self.assertEqual(before["meshes"],after["meshes"])
                self.assertEqual(len(after["skins"]),2)
                for actor in ACTORS:
                    for slot in ("body","hair","footwear"):
                        idx=before["nodes"][names[actor+"_Wardrobe_"+slot]]["mesh"]
                        for p in before["meshes"][idx]["primitives"]:
                            for semantic in ("POSITION","NORMAL","JOINTS_0","WEIGHTS_0"):
                                aid=p["attributes"][semantic]
                                self.assertEqual(accessory(before,source_bin,aid),
                                                 accessory(after,new_bin,aid))
                    for slot in ("style_top","style_bottom"):
                        idx=before["nodes"][names[actor+"_Wardrobe_"+slot]]["mesh"]
                        sx,sz=factors_for(variant,actor,slot)
                        if sx==1. and sz==1.:
                            self.assertEqual(rec["changed_style_vertices"][actor][slot],0)
                        else:
                            self.assertGreater(rec["changed_style_vertices"][actor][slot],0)
                        self.assertEqual(rec["effective_actor_factors"][actor][slot],[sx,sz])
                        for p in before["meshes"][idx]["primitives"]:
                            attrs=p["attributes"]
                            old=accessory(before,source_bin,attrs["POSITION"])
                            new=accessory(after,new_bin,attrs["POSITION"])
                            # Radius is centered on each primitive; no drag
                            # of leg separation, waist centers or body identity.
                            for axis,scale in ((0,sx),(2,sz)):
                                self.assertAlmostEqual(sum(v[axis] for v in old),
                                                       sum(v[axis] for v in new),
                                                       places=3)
                                span=max(v[axis] for v in old)-min(v[axis] for v in old)
                                new_span=max(v[axis] for v in new)-min(v[axis] for v in new)
                                self.assertAlmostEqual(new_span,span*scale,places=4)
                            for sem in ("JOINTS_0","WEIGHTS_0"):
                                self.assertEqual(accessory(before,source_bin,attrs[sem]),
                                                 accessory(after,new_bin,attrs[sem]))
                self.assertEqual(after["extras"]["radial_ablation"]["variant"],variant)

    def test_reject_output_overwrites(self):
        with self.assertRaisesRegex(ValueError,"ABLATION_SOURCE_OVERWRITE_REFUSED"):
            apply(self.root/"source.glb",self.root/"source.json",
                  self.root/"source.glb",self.root/"dup-receipt.json","lower_8")
        self.execute("lower_8","overwrite")
        with self.assertRaisesRegex(FileExistsError,"ABLATION_EXISTING_OUTPUT"):
            apply(self.root/"source.glb",self.root/"source.json",
                  self.root/"overwrite.glb",self.root/"overwrite.json","lower_8")

    def test_reject_wrong_actors_and_presets(self):
        d=json.loads((self.root/"source.json").read_text())
        d["choices"]["AsterOriginal"]="signature"
        suspect=self.root/"bad-actor-choices.json"
        suspect.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,"ABLATION_STRICT_ADVENTURE_ONLY"):
            apply(self.root/"source.glb",suspect,self.root/"bad-A.glb",
                  self.root/"bad-A.json","upper_8")

    def test_reject_tampered_source_receipt(self):
        d=json.loads((self.root/"source.json").read_text())
        d["derived_sha256"]="0"*64
        forged=self.root/"fake.json"
        forged.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,"ABLATION_SOURCE_SHA_MISMATCH"):
            apply(self.root/"source.glb",forged,self.root/"bad-B.glb",
                  self.root/"bad-B.json","lower_8")

    def test_juniper_only_does_not_move_any_aster_geometry(self):
        old,old_bin=decode(self.original)
        names={n["name"]:i for i,n in enumerate(old["nodes"])}
        for variant in ("juniper_skirt_8","juniper_skirt_14"):
            output,r=self.execute(variant,"target-"+variant)
            new,new_bin=decode(output.read_bytes())
            for slot in ("style_top","style_bottom"):
                mesh=old["meshes"][old["nodes"][names["AsterOriginal_Wardrobe_"+slot]]["mesh"]]
                for p in mesh["primitives"]:
                    for semantic in ("POSITION","NORMAL","JOINTS_0","WEIGHTS_0"):
                        attr=p["attributes"][semantic]
                        self.assertEqual(accessory(old,old_bin,attr),accessory(new,new_bin,attr))
                self.assertEqual(r["changed_style_vertices"]["AsterOriginal"][slot],0)
            self.assertEqual(r["changed_style_vertices"]["JuniperOriginal"]["style_top"],0)
            self.assertGreater(r["changed_style_vertices"]["JuniperOriginal"]["style_bottom"],0)

    def test_reject_unknown_variant(self):
        with self.assertRaisesRegex(ValueError,"ABLATION_UNKNOWN_VARIANT"):
            apply(self.root/"source.glb",self.root/"source.json",
                  self.root/"bad-C.glb",self.root/"bad-C.json","obscene_expansion")

    def test_deterministic_same_variant(self):
        a,one=self.execute("both_8","det-A")
        b,two=self.execute("both_8","det-B")
        self.assertEqual(a.read_bytes(),b.read_bytes())
        self.assertEqual(one["derived_sha256"],two["derived_sha256"])

if __name__=="__main__":
    unittest.main()
