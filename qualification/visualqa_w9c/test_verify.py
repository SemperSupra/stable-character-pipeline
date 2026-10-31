import copy,hashlib,json,unittest
from verify_projection import audit,uv
def fixture():
 s={"schema":"scp.walk_w7a_original_approach.v1","rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC","profile":"forward","fps_num":12,"fps_den":1,"actors":[]}
 names=("CobaltOriginal","MarigoldOriginal")
 for ai,name in enumerate(names):
  frames=[{"index":i,"time_num":i,"time_den":12,"root_x":(-1.65+ai*3.3)+(1-2*ai)*i*.01,"root_y":i*.01} for i in range(24)]
  s["actors"].append({"id":name,"frames":frames})
 raw=(json.dumps(s,sort_keys=True)+"\n").encode()
 cams=("OriginalFront","OriginalOblique")
 rows=[]
 for tick in range(24):
  for cam in cams:
   for actor in s["actors"]:
    f=actor["frames"][tick]
    for part,z in (("Head",2.17),("Torso",1.5),("Pelvis",1.09)):
     point=[f["root_x"],f["root_y"],z]
     rows.append({"tick":tick,"time_num":tick,"time_den":12,"camera":cam,"actor":actor["id"],
        "part":part,"xyz":point,"uv":list(uv(point,cam))})
 r={"schema":"scp.visualqa.w9c_native_same_tick.v1","rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
    "source_sha256":hashlib.sha256(raw).hexdigest(),"frames":24,"fps_num":12,"fps_den":1,
    "same_tick_camera_pairs":True,"samples":rows}
 return raw,r
class CameraFalsifiers(unittest.TestCase):
 def setUp(self):self.raw,self.r=fixture()
 def test_good_synthetic_projection_is_bounded(self):
  z=audit(self.raw,self.r);self.assertEqual(z["status"],"PASS_SYNCHRONIZED_SOURCE_PROJECTION_ONLY");self.assertEqual(z["native_synchronized_camera_sample_count"],288)
 def bad(self,code):
  with self.assertRaisesRegex(ValueError,code):audit(self.raw,self.r)
 def test_wrong_camera(self):
  self.r["samples"][0]["uv"]=[0.9,0.9];self.bad("REPROJECTION")
 def test_wrong_tick(self):
  self.r["samples"][0]["time_num"]=23;self.bad("CLOCK")
 def test_missing_sample(self):
  self.r["samples"].pop();self.bad("INCOMPLETE")
 def test_false_source_sha(self):
  self.r["source_sha256"]="0"*64;self.bad("SOURCE_SHA")
 def test_swapped_actor(self):
  self.r["samples"][0]["actor"]="MarigoldOriginal";self.bad("DUPLICATE")
 def test_false_root_position(self):
  self.r["samples"][0]["xyz"][0]+=0.05;self.bad("ROOT_DIFFERENT")
 def test_wrong_rights(self):
  self.r["rights"]="UNKNOWN";self.bad("SOURCE_SHA")
 def test_wrong_camera_pair_claim(self):
  self.r["same_tick_camera_pairs"]=False;self.bad("CLOCK_OR_PAIR")
if __name__=="__main__":unittest.main()
