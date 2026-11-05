import json
import tempfile
import unittest
from pathlib import Path
from verify_fit import aggregate,VIEWS,FRAMES,CANDIDATES

H=lambda c:c*64
def fake(folder):
  (folder/"source_receipt.json").write_text(json.dumps({
    "schema":"scp.native_neckfit_source.v1","source_reference":"SYNTHETIC_SELF_RENDER_NOT_REAL_PHOTO",
    "source_rig_bones":26,"candidate_deltas_radians":[-.6,0.,.6],"source_blend_sha256":H("a")}))
  for camera in VIEWS:
    for frame in FRAMES:
      for candidate in CANDIDATES:
        baseline=.85
        value={"m060":.74,"zero":1.0,"p060":.85}[candidate]
        # use exact rational iou 74/100, 1, 85/100
        d={"schema":"scp.render_mask_metrics.v1",
          "experiment_id":f"pony_fit_{camera}_f{frame}_{candidate}",
          "camera_id":camera,"frame_index":frame,
          "subject_class":"public_original_synthetic_equine","split":"heldout",
          "source_attestation":"UNAUTHENTICATED_SPLIT_AND_CAMERA_METADATA",
          "verdict":"MEASURED_ONLY_NOT_ANATOMICAL_ACCEPTANCE",
          "width":256,"height":256,"reference_foreground_pixels":10000,
          "reference_sha256":H("a"),"baseline_image_sha256":H("b"),
          "candidate_image_sha256":H("c"),"baseline_sha256":H("d"),"candidate_sha256":H("e"),
          "baseline":{"intersection_pixels":85,"union_pixels":100,"iou":baseline},
          "candidate":{"intersection_pixels":int(value*100),"union_pixels":100,"iou":value}}
        (folder/f"measurement_{camera}_f{frame}_{candidate}.json").write_text(json.dumps(d))

class Quality(unittest.TestCase):
 def setUp(self):
   self.temp=tempfile.TemporaryDirectory()
   self.root=Path(self.temp.name)
   fake(self.root)
 def tearDown(self):self.temp.cleanup()
 def test_aggregate(self):
   r=aggregate(self.root)
   self.assertEqual(r["best_candidate"],"zero")
   self.assertEqual(r["camera_count"],2)
   self.assertEqual(r["external_photo_fit"],"NOT_RUN")
 def test_missing(self):
   next(self.root.glob("measurement_*.json")).unlink()
   with self.assertRaises(OSError):aggregate(self.root)
 def test_wrong_camera(self):
   p=next(self.root.glob("measurement_*.json"));r=json.loads(p.read_text());r["camera_id"]="other";p.write_text(json.dumps(r))
   with self.assertRaises(ValueError):aggregate(self.root)
 def test_bad_iou(self):
   p=next(self.root.glob("measurement_*.json"));r=json.loads(p.read_text());r["candidate"]["iou"]=1.01;p.write_text(json.dumps(r))
   with self.assertRaises(ValueError):aggregate(self.root)
 def test_fake_attestation(self):
   p=next(self.root.glob("measurement_*.json"));r=json.loads(p.read_text());r["source_attestation"]="VERIFIED";p.write_text(json.dumps(r))
   with self.assertRaises(ValueError):aggregate(self.root)
 def test_bad_per_view_reference(self):
   p=self.root/"measurement_side_f12_zero.json";r=json.loads(p.read_text());r["reference_sha256"]=H("f");p.write_text(json.dumps(r))
   with self.assertRaises(ValueError):aggregate(self.root)
 def test_failure_if_candidate_not_improved(self):
   p=self.root/"measurement_side_f12_zero.json";r=json.loads(p.read_text())
   r["candidate"]={"intersection_pixels":80,"union_pixels":100,"iou":.8}
   p.write_text(json.dumps(r))
   with self.assertRaises(ValueError):aggregate(self.root)

if __name__=="__main__":unittest.main()
