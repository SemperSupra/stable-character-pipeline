#!/usr/bin/env python3
"""Adversarial source-original PBR appearance tests, no protected models."""
import copy
import hashlib
import json
import tempfile
from pathlib import Path
import unittest

import parameters_v1 as c
import morph_preview_35_v1 as morph
import appearance_material_v1 as pbr
from verify_original_glb import decode


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.a=c.sample(73,"AsterTest")
        self.j=c.sample(74,"JuniperTest")
        self.glb=self.folder/"source.glb"
        self.manifest=self.folder/"source.json"
        self.build_receipt=self.folder/"source_receipt.json"
        morph.build(self.a,self.j,self.glb,self.manifest,self.build_receipt)

    def test_source_bytes_rig_skin_and_anim_preserved(self):
        original=self.glb.read_bytes()
        before, bin_before=decode(original)
        out,witness=pbr.apply(original,self.a,self.j)
        after, bin_after=decode(out)
        self.assertEqual(bin_after[:len(bin_before)],bin_before)
        self.assertEqual(before["skins"],after["skins"])
        self.assertEqual(before["animations"],after["animations"])
        self.assertEqual(before["nodes"],after["nodes"])
        self.assertEqual(len(after["meshes"]),len(before["meshes"]))
        self.assertEqual(before["materials"],after["materials"][:len(before["materials"])])
        self.assertEqual(set(witness),set(pbr.ACTORS))
        self.assertEqual(len(witness["AsterOriginal"]["material_names"]),4)
        self.assertTrue(witness["JuniperOriginal"]["per_eye_iris_materials"])

    def test_per_eye_and_per_actor_color_independence(self):
        source=self.glb.read_bytes()
        baseline,_=pbr.apply(source,self.a,self.j)
        altered=copy.deepcopy(self.a)
        altered["appearance"]["left_iris_rgb"]=[0.99,.01,.01]
        different,_=pbr.apply(source,altered,self.j)
        self.assertNotEqual(hashlib.sha256(baseline).digest(),hashlib.sha256(different).digest())
        d0,_=decode(baseline);d1,_=decode(different)
        b={m["name"]:m for m in d0["materials"]}
        a={m["name"]:m for m in d1["materials"]}
        left="AsterOriginal_left_iris_parametric"
        right="AsterOriginal_right_iris_parametric"
        other="JuniperOriginal_left_iris_parametric"
        self.assertNotEqual(b[left],a[left])
        self.assertEqual(b[right],a[right])
        self.assertEqual(b[other],a[other])
        self.assertEqual(d0["skins"],d1["skins"])

    def test_reject_unknown_rights_and_existing_output(self):
        source=self.glb.read_bytes()
        d,b=decode(source)
        d["extras"]["source_class"]="RESTRICTED_EXTERNAL"
        import rig35_v2
        poisoned=rig35_v2.glb_pack(d,b)
        with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_REJECTED"):
            pbr.apply(poisoned,self.a,self.j)
        out=self.folder/"appearance.glb"
        receipt=self.folder/"appearance.json"
        result=pbr.build(self.glb,out,receipt,self.a,self.j)
        self.assertTrue(out.exists())
        self.assertEqual(result["joints_each"],35)
        self.assertFalse(result["human_visual_accepted"])
        self.assertFalse(result["release_approved"])
        self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(),
                         json.loads(receipt.read_text())["derived_sha256"])
        with self.assertRaises(FileExistsError):
            pbr.build(self.glb,out,receipt,self.a,self.j)

    def test_stylized_undertone_and_roughness_independent(self):
        source=self.glb.read_bytes()
        baseline,_=pbr.apply(source,self.a,self.j)
        other=copy.deepcopy(self.a)
        other["appearance"]["skin_undertone"]="olive" if other["appearance"]["skin_undertone"]!="olive" else "cool"
        other["appearance"]["skin_roughness"]=.22
        updated,_=pbr.apply(source,other,self.j)
        first,_=decode(baseline);second,_=decode(updated)
        m="AsterOriginal_skinWarm_parametric"
        original_material=next(x for x in first["materials"] if x["name"]==m)
        next_material=next(x for x in second["materials"] if x["name"]==m)
        self.assertNotEqual(original_material,next_material)


if __name__=="__main__":
    unittest.main(verbosity=2)
