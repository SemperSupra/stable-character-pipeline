import unittest,copy
from annotate import project,sidecar,CAMERAS,camera_receipt
class SourceProjection(unittest.TestCase):
 def test_calibration_wrong_camera_not_self_pass(self):
  p=(.4,.2,1.3)
  self.assertGreater(sum(abs(a-b) for a,b in zip(project(p,"OriginalFront"),project(p,"OriginalOblique"))),.001)
 def test_offscreen_is_not_visible(self):
  p=(500,0,1);uv=project(p,"OriginalFront")
  self.assertFalse(0<=uv[0]<=1)
 def test_missing_source_rejected(self):
  with self.assertRaisesRegex(ValueError,"SOURCE_ID_RIGHTS"):
   camera_receipt({"rights":"UNKNOWN"}, {"cameras":[]})
 def test_wrong_camera_probe_rejected(self):
  source={"schema":"scp.walk_w7a_original_approach.v1","rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC","actors":[{"id":"A","frames":[{"root_x":0,"root_y":0}]} ,{"id":"B","frames":[{"root_x":1,"root_y":0}]}]}
  render={"cameras":[{"camera":"OriginalFront","core_body_camera_projection":[{"actor":"A","part":"Head","uv":[.9,.9]}]}]}
  with self.assertRaisesRegex(ValueError,"CALIBRATION"):
   camera_receipt(source,render)
if __name__=="__main__":unittest.main()
