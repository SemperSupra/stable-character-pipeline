import math,unittest
from contact_policy import point,plan,root_velocity
class RootOnlyContact(unittest.TestCase):
 def test_flat_immobile(self):
  t=[{"x_negative":point(0,(0,0)),"x_positive":point(.08,(1,0))} for _ in range(5)]
  r=plan(t)
  self.assertEqual(r["max_simultaneous_contact_conflict_lower_bound_m"],0.)
  self.assertTrue(all(row["root_offset_m"]==(0.,0.,0.) for row in r["frames"]))
 def test_deep_negative_lift_is_bounded(self):
  t=[{"x_negative":point(-.06,(0,0)),"x_positive":point(.05,(1,0))} for _ in range(4)]
  r=plan(t)
  self.assertAlmostEqual(r["frames"][0]["root_offset_m"][2],.06)
  self.assertFalse(r["gait_accepted"])
 def test_double_plant_root_conflict(self):
  t=[]
  for i in range(6):
   t.append({"x_negative":point(0,(i*.02,0)),"x_positive":point(0,(1-i*.02,0))})
  r=plan(t)
  self.assertGreater(r["max_simultaneous_contact_conflict_lower_bound_m"],.05)
  self.assertLessEqual(max(math.hypot(*row["root_offset_m"][:2]) for row in r["frames"]),.12+1e-12)
 def test_root_velocity_reports_frame_discontinuities(self):
  t=[{"x_negative":point(0,(i*.03,0)),"x_positive":point(.1,(0,0))} for i in range(5)]
  r=plan(t)
  self.assertGreater(root_velocity(r["frames"],12),.05)
 def test_excess_lift_unknown(self):
  t=[{"x_negative":point(-.3,(0,0)),"x_positive":point(0,(1,0))} for _ in range(4)]
  with self.assertRaisesRegex(ValueError,"NECESSARY_LIFT_EXCEEDS"):plan(t)
 def test_nonfinite_rejected(self):
  t=[{"x_negative":point(0,(0,0)),"x_positive":point(0,(1,0))} for _ in range(4)]
  t[1]["x_negative"]["z_m"]=float("nan")
  with self.assertRaisesRegex(ValueError,"BAD_Z"):plan(t)
 def test_mislabeled_partition_rejected(self):
  with self.assertRaisesRegex(ValueError,"BAD_SHOE_PARTITIONS"):
   plan([{"left":point(0,(0,0))} for _ in range(4)])
 def test_unknown_timebase(self):
  with self.assertRaisesRegex(ValueError,"INVALID_FPS"):root_velocity([{"root_offset_m":(0,0,0)},{"root_offset_m":(.1,0,0)}],0)
if __name__=="__main__":unittest.main()
