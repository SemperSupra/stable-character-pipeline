"""Independent negative controls for bounded HOG input and scientific abstention."""
import copy,unittest
import numpy as np
import cv2
from clean_hog import CAMERAS,EXPECTED,MODEL_SHA256,validate_boxes,model
class CleanHogControls(unittest.TestCase):
 def test_all_pins_complete_and_distinct(self):
  self.assertEqual(len(MODEL_SHA256),64)
  for profile,row in EXPECTED.items():
   for key,digest in row.items():self.assertEqual(len(digest),64,(profile,key))
   self.assertNotEqual(row[CAMERAS[0]],row[CAMERAS[1]])
 def test_wrong_model_metadata_rejected(self):
  h=model()
  self.assertIsNotNone(h)
  self.assertEqual(len(cv2.HOGDescriptor_getDefaultPeopleDetector()),3781)
 def test_empty_original_frame_does_not_create_true_human(self):
  h=model();canvas=np.zeros((360,640,3),dtype=np.uint8)
  boxes,weights=h.detectMultiScale(canvas,winStride=(8,8),padding=(8,8),scale=1.05)
  self.assertEqual(len(validate_boxes(boxes,weights,canvas.shape)),0)
 def test_boxes_must_be_finite_and_in_frame(self):
  with self.assertRaisesRegex(ValueError,"OUTSIDE"):
   validate_boxes([(700,0,30,100)],[1.],(360,640,3))
  with self.assertRaisesRegex(ValueError,"COUNT"):
   validate_boxes([(20,10,30,100)],[],(360,640,3))
 def test_two_boxes_do_not_imply_gait_or_actor_id(self):
  boxes=validate_boxes([(0,0,64,128),(120,0,64,128)],[.7,.8],(360,640,3))
  self.assertEqual(len(boxes),2)
  self.assertTrue(all("actor_id" not in x for x in boxes))
if __name__=="__main__":unittest.main()
