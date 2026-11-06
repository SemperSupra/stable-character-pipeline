#!/usr/bin/env python3
"""Original synthetic 35-joint GLB read-only independent regression tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/"original_reusable_characters"
sys.path.insert(0,str(SOURCE))
from modular_wardrobe_v1 import build
from rig35_v2 import glb_pack
from verify_original_glb import decode
from observe import analyze, InvalidModel, load_glb

class OriginalHumanTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.t=tempfile.TemporaryDirectory()
  cls.g=Path(cls.t.name)/"original_wardrobe.glb"
  cls.m=Path(cls.t.name)/"original_wardrobe.json"
  build(cls.g,cls.m)
  cls.raw=cls.g.read_bytes()
 @classmethod
 def tearDownClass(cls):cls.t.cleanup()
 def mutate(self,fn):
  d,b=decode(self.raw)
  fn(d)
  return glb_pack(d,b)
 def test_real_source_35_joint_72_frame(self):
  r=analyze(self.raw)
  self.assertEqual(set(r["actors"]),{"AsterOriginal","JuniperOriginal"})
  self.assertTrue(all(v["joint_count"]==35 for v in r["actors"].values()))
  self.assertEqual(r["frame_count"],72)
  self.assertFalse(r["model_mutation"])
  self.assertEqual(r["photo_fit"],"NOT_RUN")
  self.assertFalse(r["visual_acceptance"])
 def test_bad_header(self):
  with self.assertRaises(InvalidModel):analyze(b"not a glb")
 def test_reject_fake_source_rights(self):
  x=self.mutate(lambda d:d["extras"].update(source_class="UNKNOWN_THIRD_PARTY"))
  with self.assertRaises(InvalidModel):analyze(x)
 def test_reject_fabricated_visual_acceptance(self):
  x=self.mutate(lambda d:d["extras"]["wardrobe_contract"].update(appearance_approved=True))
  with self.assertRaises(InvalidModel):analyze(x)
 def test_reject_missing_joint(self):
  x=self.mutate(lambda d:d["skins"][0]["joints"].pop())
  with self.assertRaises(InvalidModel):analyze(x)
 def test_reject_garment_wrong_actor_skin(self):
  def f(d):
   for node in d["nodes"]:
    if node.get("name")=="AsterOriginal_Wardrobe_top":node["skin"]=1;return
   raise RuntimeError("garment missing")
  x=self.mutate(f)
  with self.assertRaises(InvalidModel):analyze(x)
 def test_reject_body_garment_same_mesh(self):
  def f(d):
   names={n["name"]:n for n in d["nodes"]}
   names["AsterOriginal_Wardrobe_top"]["mesh"]=names["AsterOriginal_Wardrobe_body"]["mesh"]
  with self.assertRaises(InvalidModel):analyze(self.mutate(f))
 def test_reject_cyclic_hierarchy(self):
  def f(d):
   root=next(i for i,n in enumerate(d["nodes"]) if n["name"]=="AsterOriginal_SceneRoot")
   d["nodes"][root].setdefault("children",[]).append(root)
  with self.assertRaises(InvalidModel):analyze(self.mutate(f))
 def test_reject_animation_tamper(self):
  def f(d):
   d["animations"][0]["channels"].clear()
  with self.assertRaises(InvalidModel):analyze(self.mutate(f))
if __name__=="__main__":unittest.main()
