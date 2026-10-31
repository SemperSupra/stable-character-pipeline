import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from pixel_approach import centroid,geometry,MotionError
def source():
 frames=lambda x:[{"index":i,"time_num":i,"time_den":12,"root_x":x+(i/23)*(0.33 if x<0 else -0.33)} for i in range(24)]
 return {"rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC","fps_num":12,"fps_den":1,
  "actors":[{"id":"CobaltOriginal","frames":frames(-1.65)},
            {"id":"MarigoldOriginal","frames":frames(1.65)}]}
class OriginalSyntheticApproach(unittest.TestCase):
 def test_original_source_root_converges(self):
  self.assertAlmostEqual(geometry(source())[0]-geometry(source())[1],0.66,places=3)
 def test_wrong_original_actor_fails(self):
  s=source();s["actors"][1]["id"]="FORGED_PERSON"
  with self.assertRaisesRegex(MotionError,"ACTOR_IDENTITY"):geometry(s)
 def test_wrong_clock_fails(self):
  s=source();s["fps_den"]=2
  with self.assertRaisesRegex(MotionError,"CLOCK"):geometry(s)
 def test_static_source_fails(self):
  s=source()
  for a in s["actors"]:
   for x in a["frames"]:x["root_x"]=a["frames"][0]["root_x"]
  with self.assertRaisesRegex(MotionError,"NO_SIGNIFICANT_ROOT_APPROACH"):geometry(s)
 def test_two_colours_separately_detected(self):
  width,height=10,10;pix=bytearray(width*height*3)
  for y in range(height):
   for x in range(5):
    i=(y*width+x)*3;pix[i:i+3]=bytes((20,90,180))
   for x in range(5,10):
    i=(y*width+x)*3;pix[i:i+3]=bytes((150,65,20))
  self.assertLess(centroid(pix,width,height,"blue",1),centroid(pix,width,height,"brown",1))
 def test_missing_actor_pixels_fail(self):
  with self.assertRaisesRegex(MotionError,"INSUFFICIENT"):centroid(bytes(10*10*3),10,10,"blue",1)
if __name__=="__main__":unittest.main()
