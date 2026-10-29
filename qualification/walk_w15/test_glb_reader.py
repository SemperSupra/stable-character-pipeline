"""W15 source-clean pure stdlib GLB decoder hostile tests."""
import copy,json,os,struct,unittest
from pathlib import Path
from pure_glb_reader import accessor,evaluate,mul,mv,read_glb,trs
class GltfReadbackControls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.path=os.environ["W15_GLB"]
  cls.doc,cls.binary,cls.sha=read_glb(cls.path)
 def test_native_two_actor_source_skin(self):
  for second in (0,1,2,3,4,5,71/12):
   data=evaluate(self.doc,self.binary,second)
   self.assertEqual(set(data),{"CobaltOriginal","MarigoldOriginal"})
   self.assertTrue(all(len(v)==28 for v in data.values()))
 def test_reject_corrupt_glb_magic(self):
  raw=bytearray(Path(self.path).read_bytes());raw[:4]=b"POOF"
  tmp=Path(os.environ["W15_TMP"])/"mutated.glb"
  tmp.write_bytes(raw)
  with self.assertRaisesRegex(ValueError,"GLB_MAGIC"):read_glb(tmp)
 def test_reject_malformed_accessor_bounds(self):
  doc=copy.deepcopy(self.doc)
  item=doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
  doc["accessors"][item]["count"]=999999
  with self.assertRaisesRegex(ValueError,"ACCESSOR_BOUNDS"):accessor(doc,self.binary,item)
 def test_reject_wrong_skin_index(self):
  doc=copy.deepcopy(self.doc);doc["skins"][0]["joints"]=[999,998]
  with self.assertRaises((IndexError,KeyError,ValueError)):evaluate(doc,self.binary,0)
 def test_reject_duplicate_animation_channel(self):
  doc=copy.deepcopy(self.doc)
  doc["animations"][0]["channels"].append(copy.deepcopy(doc["animations"][0]["channels"][0]))
  with self.assertRaisesRegex(ValueError,"OVERLAPPING_ANIMATION_CHANNELS"):evaluate(doc,self.binary,0)
 def test_reject_skinning_weights_mutation(self):
  doc=copy.deepcopy(self.doc);a=doc["meshes"][0]["primitives"][0]["attributes"]["WEIGHTS_0"]
  attr=doc["accessors"][a];view=doc["bufferViews"][attr["bufferView"]]
  off=view.get("byteOffset",0)+attr.get("byteOffset",0)
  data=bytearray(self.binary);struct.pack_into("<f",data,off,.23)
  with self.assertRaisesRegex(ValueError,"SKIN_WEIGHTS_NOT_NORMALIZED"):evaluate(doc,bytes(data),0)
 def test_reject_quaternion_zero(self):
  with self.assertRaisesRegex(ValueError,"INVALID_ROTATION_QUATERNION"):
   trs((0,0,0),(0,0,0,0),(1,1,1))
 def test_matrix_translation_order(self):
  t=trs((2,3,4),(0,0,0,1),(1,1,1))
  self.assertEqual(mv(t,(0,0,0,1)),(2,3,4,1))
 def test_reject_scene_parent_cycle(self):
  doc=copy.deepcopy(self.doc)
  doc["nodes"][0]["children"]=[1]
  with self.assertRaisesRegex(ValueError,"NODE_MULTIPLE_PARENTS|CYCLIC_JOINT_HIERARCHY"):evaluate(doc,self.binary,0)
if __name__=="__main__":unittest.main()
