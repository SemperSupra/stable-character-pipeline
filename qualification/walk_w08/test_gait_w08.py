"""W08 original public bilateral walk control-plane regression."""
import math,unittest
import gait_w08 as w08
class OriginalEasedFootGait(unittest.TestCase):
 def test_rights_clock_and_planted_foot_lock(self):
  for profile in ("relaxed","brisk"):
   m=w08.generate(profile)
   self.assertEqual((m["schema"],m["source_rights"]),("scp.walk_motion.v1","ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY"))
   self.assertEqual((len(m["frames"]),m["fps"]),(72,12))
   v=w08.w06.validate(m)
   self.assertLessEqual(v["contact_slip_max_scene_units"],1e-7)
   self.assertGreaterEqual(v["minimum_root_separation_scene_units"],1.5)
 def test_stop_easing_bounded_discrete_acceleration(self):
  for profile in ("relaxed","brisk"):
   m=w08.generate(profile)
   for actor in m["actors"]:
    id=actor["id"]
    x=[f["actors"][id]["root_x"] for f in m["frames"]]
    velocity=[(b-a)*12 for a,b in zip(x,x[1:])]
    acceleration=max(abs(b-a)*12 for a,b in zip(velocity,velocity[1:]))
    self.assertLess(acceleration,1.0)
    self.assertGreater(abs(x[-1]-x[0]),1.7)
 def test_reduced_projected_ankle_overlap(self):
  m=w08.generate("relaxed")
  for actor in m["actors"]:
   id=actor["id"]
   overlap=sum(abs(f["actors"][id]["joints"]["ankle_left"][0]-f["actors"][id]["joints"]["ankle_right"][0])<.16 for f in m["frames"])
   self.assertLess(overlap,35)
   self.assertGreater(overlap,0)
 def test_not_3d_or_human(self):
  m=w08.generate("relaxed")
  self.assertEqual(m["geometry_space"],"STYLIZED_CAMERA_XY_UNCALIBRATED")
  self.assertEqual(m["real_body_kinematics"],"NOT_EVALUATED")
 def test_original_gait_function_restoration(self):
  before=w08.w06.root_at
  before_foot=w08.w06.foot_at
  w08.generate("brisk")
  self.assertIs(before,w08.w06.root_at)
  self.assertIs(before_foot,w08.w06.foot_at)
if __name__=="__main__":unittest.main()
