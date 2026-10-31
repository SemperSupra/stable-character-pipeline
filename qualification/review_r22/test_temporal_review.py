"""Independent R22 temporal falsifiers; expected RED on R21 endpoint-only checks.

Tests intentionally exercise the unchanged public-original-synthetic R21 source.
No protected R009 original, biological gait or identity inference.
"""
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"review_r21"))
from pixel_approach import geometry,raw_h264,MotionError
from test_pixel_approach import source

class TemporalReviewer(unittest.TestCase):
 def test_mid_sequence_source_root_teleport_must_fail(self):
  s=source()
  s["actors"][0]["frames"][12]["root_x"]=999.0
  with self.assertRaisesRegex(MotionError,"SOURCE_FRAME_TELEPORT"):
   geometry(s)
 def test_nonfinite_middle_source_must_fail(self):
  s=source()
  s["actors"][1]["frames"][7]["root_x"]=float("nan")
  with self.assertRaisesRegex(MotionError,"SOURCE_NONFINITE_FRAME"):
   geometry(s)
 def test_decoded_video_must_return_every_one_of_24_frames(self):
  width,height=640,360
  frame=bytes(width*height*3)
  ffprobe=b'{"streams":[{"width":640,"height":360,"nb_frames":"24","r_frame_rate":"12/1","codec_name":"h264"}]}'
  with patch("pixel_approach.subprocess.check_output",side_effect=[ffprobe,frame*24]):
   frames=raw_h264(Path("synthetic-original.mp4"))
  self.assertEqual(len(frames),24,"FIRST_RED_MIDDLE_22_VIDEO_FRAMES_SILENTLY_SKIPPED")
 def test_unchanged_source_continuity_accepts_original_synthetic(self):
  g=geometry(source())
  self.assertAlmostEqual(g[0]-g[-1],0.66,places=3)
if __name__=="__main__":unittest.main()
