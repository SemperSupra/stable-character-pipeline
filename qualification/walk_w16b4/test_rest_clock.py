import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from rest_clock import build
def fixture():
 # Exact B3 Go generator is the source in CI; test negative uses its receipt.
 return json.loads(Path(sys.argv[-1]).read_text()) if len(sys.argv)>1 and sys.argv[-1].endswith(".json") else None
class Hostile(unittest.TestCase):
 def setUp(self):
  import os
  p=os.environ.get("B3_SOURCE")
  if not p:self.skipTest("B3_SOURCE not supplied")
  self.original=Path(p).read_bytes()
 def test_correct(self):
  x=build(self.original)
  self.assertEqual(x["status"],"PASS_SOURCE_ONLY_TYPED_REST_AND_CLOCK")
  self.assertEqual(x["max_local_fk_source_unit"]<1e-8,True)
  self.assertEqual(len(x["actors"]),2)
  for a in x["actors"]:
   self.assertEqual(len(a["rest_bones"]),4)
   self.assertEqual(len(a["frames"]),7)
   for f in a["frames"]:
    self.assertEqual(len(f["bone_local_quats"]),4)
    self.assertEqual(f["sample_index_48k"],f["index"]*4000)
 def test_adversarial_input(self):
  base=json.loads(self.original)
  def clone():return copy.deepcopy(base)
  mutations={
   "rights":lambda x:x.update(Rights="UNADMITTED"),
   "fps":lambda x:x.update(FPSNum=24),
   "time":lambda x:x["Actors"][0]["Frames"][1].update(TimeDen=24),
   "parent":lambda x:x["Actors"][0]["Frames"][0]["Legs"][0].update(Parent="Unknown"),
   "contact":lambda x:x["Actors"][0]["Frames"][0]["Legs"][1].update(Contact="stance"),
   "basis":lambda x:x.update(Basis="GLTF_Y_UP"),
   "origin":lambda x:x.update(OriginSHA="fake"),
   "identity":lambda x:x["Actors"][1].update(ID="CobaltOriginal"),
   "quat":lambda x:x["Actors"][0]["Frames"][1]["Legs"][0].update(UpperWorld=[0,0,0,0])
  }
  for name,mut in mutations.items():
   x=clone();mut(x)
   with self.subTest(name=name):
    with self.assertRaises(ValueError):build(json.dumps(x).encode())
if __name__=="__main__":unittest.main()
