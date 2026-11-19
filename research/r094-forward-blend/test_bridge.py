import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from bridge_contract import ACTORS,FRAMES,compare
def fixture():
 actors={}
 for name in ACTORS:
  actors[name]=[{"frame":f,"native_rig_bones":163,"body":{"sha256":str(f),"n":9321},
    "rig_pose_sha256":str(f),"clothes":{c:{"n":301,"sha256":str(f)} for c in ["top","pants","shoes"]}} for f in FRAMES]
 return {"schema":"scp.r094.blender-4-5-native-scene-baseline.v1",
  "scene_sha256":"a"*64,"blender_version":"4.5.16","observations":actors}
class TestBridge(unittest.TestCase):
 def test_equal(self):
  a=fixture();self.assertTrue(compare(a,copy.deepcopy(a["observations"]),"a"*64))
 def test_forged_source(self):
  a=fixture()
  with self.assertRaisesRegex(ValueError,"SCENE_SHA"):compare(a,a["observations"],"b"*64)
 def test_wrong_source_version(self):
  a=fixture();a["blender_version"]="5.2.4"
  with self.assertRaisesRegex(ValueError,"NOT_4_5"):compare(a,a["observations"],"a"*64)
 def test_replaced_shoe_mesh(self):
  a=fixture();b=copy.deepcopy(a["observations"])
  b[ACTORS[0]][1]["clothes"]["shoes"]["sha256"]="FORGED"
  with self.assertRaisesRegex(ValueError,"GARMENT_DRIFT"):compare(a,b,"a"*64)
 def test_missing_frame(self):
  a=fixture();b=copy.deepcopy(a["observations"]);b[ACTORS[0]].pop()
  with self.assertRaisesRegex(ValueError,"FRAME"):compare(a,b,"a"*64)
 def test_malformed_rig(self):
  a=fixture();b=copy.deepcopy(a["observations"]);b[ACTORS[1]][0]["native_rig_bones"]=17
  with self.assertRaisesRegex(ValueError,"163"):compare(a,b,"a"*64)
if __name__=="__main__":unittest.main()
