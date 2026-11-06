"""Fail-closed tests for owner-directed fictional facial param controls."""
import copy
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from facial_detail_v2 import ACTORS, BOUNDS, DEFAULT, derive, profiles_valid, sculpt
from facial_detail_v2 import SCHEMA
from modular_wardrobe_v1 import build
from parametric_morphology_v1 import apply
from verify_original_glb import decode, accessory


class FaceControlsV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        cls.base=cls.root/"original.glb"
        cls.base_manifest=cls.root/"original.json"
        build(cls.base,cls.base_manifest)
        cls.morph=cls.root/"morph.glb"
        cls.morph_manifest=cls.root/"morph.json"
        apply(cls.base,cls.base_manifest,cls.morph,cls.morph_manifest,
              cls.root/"morph-receipt.json")
        cls.morph_sha=hashlib.sha256(cls.morph.read_bytes()).hexdigest()
        cls.derive_counter=0

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def make(self,profiles=None):
        self.__class__.derive_counter+=1
        prefix=f"face{self.derive_counter:03}"
        dest=self.root/(prefix+".glb")
        meta=self.root/(prefix+".json")
        rec=self.root/(prefix+".receipt.json")
        return derive(self.morph,self.morph_manifest,dest,meta,rec,profiles),dest,meta,rec

    def test_owner_defaults_are_bounded_independent_controls(self):
        p=profiles_valid(DEFAULT)
        self.assertEqual(set(p),set(ACTORS))
        self.assertEqual(set(p[ACTORS[0]]),set(BOUNDS))
        self.assertEqual(set(p[ACTORS[1]]),set(BOUNDS))
        self.assertNotEqual(p[ACTORS[0]]["eye_width"],p[ACTORS[1]]["eye_width"])
        self.assertNotEqual(p[ACTORS[0]]["nose_width"],p[ACTORS[1]]["nose_width"])

    def test_actual_source_face_meshes_move_without_changing_35_joint_skin(self):
        r,out,meta,receipt=self.make()
        self.assertEqual(r["input_sha256"],self.morph_sha)
        self.assertFalse(r["native_visual_accepted"])
        self.assertFalse(r["sex_inferred_from_images"])
        self.assertTrue(r["skin_armature_animation_preserved"])
        self.assertEqual(r["schema"],SCHEMA+".receipt")
        self.assertEqual(r["derived_sha256"],hashlib.sha256(out.read_bytes()).hexdigest())
        original,_=decode(self.morph.read_bytes())
        changed,_=decode(out.read_bytes())
        self.assertEqual(original["skins"],changed["skins"])
        self.assertEqual(original["animations"],changed["animations"])
        self.assertEqual(len(changed["skins"]),2)
        self.assertEqual([len(s["joints"]) for s in changed["skins"]],[35,35])
        self.assertEqual(original["nodes"],changed["nodes"])
        self.assertEqual(original["meshes"],changed["meshes"])
        self.assertEqual(original["materials"],changed["materials"])
        self.assertEqual(original["scenes"],changed["scenes"])
        for actor in ACTORS:
            observations=r["vertex_changes_by_material"][actor]
            for key in ("eyeWhite","iris",
                        "skinWarm" if actor=="AsterOriginal" else "skinCool",
                        "ebonyHair" if actor=="AsterOriginal" else "chestnutHair"):
                self.assertGreater(observations.get(key,0),0,(actor,key))
        self.assertEqual(hashlib.sha256(self.morph.read_bytes()).hexdigest(),self.morph_sha)
        self.assertEqual(json.loads(meta.read_text())["facial_source_sha256"],self.morph_sha)
        self.assertEqual(json.loads(receipt.read_text())["derived_sha256"],
                         r["derived_sha256"])

    def test_deterministic_bytes(self):
        r1,p1,_,_=self.make()
        r2,p2,_,_=self.make()
        self.assertEqual(r1["derived_sha256"],r2["derived_sha256"])
        self.assertEqual(p1.read_bytes(),p2.read_bytes())

    def test_no_spurious_below_neck_skin_change(self):
        p=profiles_valid(DEFAULT)[ACTORS[0]]
        # Source geometry at pelvis, forearm, underbust, chin boundary
        for x,y,z in ((.08,.85,-.07),(.20,1.35,.01),(.05,1.2,-.11),(.04,1.50,-.04)):
            self.assertEqual(sculpt((x,y,z),"skinWarm",p),(x,y,z))
        # A localized face point must change; not a world-scale body warp.
        point=(.04,1.666,-.102)
        self.assertNotEqual(sculpt(point,"eyeWhite",p),point)
        self.assertEqual(sculpt((.04,1.735,-.12),"ebonyHair",p),(.04,1.735,-.12))

    def test_independent_control_edit_reaches_glb(self):
        p=copy.deepcopy(DEFAULT)
        r1,_,_,_=self.make(p)
        p["AsterOriginal"]["eye_width"]=1.22
        r2,_,_,_=self.make(p)
        self.assertNotEqual(r1["derived_sha256"],r2["derived_sha256"])
        self.assertNotEqual(p["AsterOriginal"]["eye_width"],
                            DEFAULT["AsterOriginal"]["eye_width"])

    def test_invalid_profiles_fail_closed(self):
        invalid=[]
        a=copy.deepcopy(DEFAULT);a.pop("JuniperOriginal");invalid.append(a)
        a=copy.deepcopy(DEFAULT);a["AsterOriginal"]["eye_width"]=float("nan");invalid.append(a)
        a=copy.deepcopy(DEFAULT);a["JuniperOriginal"]["eye_height"]=100.;invalid.append(a)
        a=copy.deepcopy(DEFAULT);a["JuniperOriginal"]["eye_height"]=True;invalid.append(a)
        a=copy.deepcopy(DEFAULT);a["JuniperOriginal"]["bad"]=2;invalid.append(a)
        for case in invalid:
            with self.assertRaisesRegex(ValueError,"FACE_"):
                profiles_valid(case)

    def test_refuse_source_overwrite_and_existing_outputs(self):
        with self.assertRaisesRegex(ValueError,"FACE_SOURCE_OVERWRITE"):
            derive(self.morph,self.morph_manifest,self.morph,
                   self.root/"should-not-exist.json",self.root/"should-not.json")
        r,out,meta,receipt=self.make()
        with self.assertRaisesRegex(FileExistsError,"FACE_REFUSE_OVERWRITE"):
            derive(self.morph,self.morph_manifest,out,meta,receipt)

    def test_forged_manifest_digest_rejected(self):
        corrupted=json.loads(self.morph_manifest.read_text())
        corrupted["derived_sha256"]="0"*64
        forged=self.root/"forged-morph.json"
        forged.write_text(json.dumps(corrupted))
        with self.assertRaisesRegex(ValueError,"FACE_SOURCE_MANIFEST_SHA"):
            derive(self.morph,forged,self.root/"forged.glb",
                   self.root/"forged.json",self.root/"forged-receipt.json")


if __name__=="__main__":
    unittest.main()
