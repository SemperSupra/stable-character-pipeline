import copy,sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from contact_rays import separate_sole,validate_sole,occlusion,FRAMES,ACTORS
class Hostile(unittest.TestCase):
 def test_original_explicit_sole(self):
  r=validate_sole(separate_sole())
  self.assertEqual((r["stance"],r["swing"]),(3,2))
 def test_fabricated_rights(self):
  s=separate_sole();s["rights"]="PRIVATE_UNADMITTED"
  with self.assertRaisesRegex(ValueError,"RIGHTS"):validate_sole(s)
 def test_labeled_source_spoof(self):
  s=separate_sole();s["source"]="NATIVE_C2_HEEL_TOE"
  with self.assertRaisesRegex(ValueError,"FALSE_NATIVE"):validate_sole(s)
 def test_slipping_heel(self):
  s=separate_sole();s["frames"][1]["landmarks"]["heel"][0]+=.01
  with self.assertRaisesRegex(ValueError,"ANCHOR_SLIP"):validate_sole(s)
 def test_false_plant_hovers(self):
  s=separate_sole();s["frames"][2]["landmarks"]["toe"][2]=.2
  with self.assertRaisesRegex(ValueError,"FALSE_STANCE_HOVER"):validate_sole(s)
 def test_fake_swing_lowers_to_ground(self):
  s=separate_sole();s["frames"][3]["landmarks"]["heel"][2]=.001
  with self.assertRaisesRegex(ValueError,"SWING_CLEARANCE"):validate_sole(s)
 def test_negative_ground_penetration(self):
  s=separate_sole();s["frames"][2]["landmarks"]["toe"][2]=-.01
  with self.assertRaisesRegex(ValueError,"GROUND_PENETRATION"):validate_sole(s)
 def test_clock_mismatch(self):
  s=separate_sole();s["frames"][1]["time_den"]=24
  with self.assertRaisesRegex(ValueError,"SOLE_CLOCK"):validate_sole(s)
 def test_nonfinite(self):
  s=separate_sole();s["frames"][0]["landmarks"]["toe"][2]=math.inf
  with self.assertRaisesRegex(ValueError,"NONFINITE"):validate_sole(s)
 def test_missing_toe(self):
  s=separate_sole();del s["frames"][2]["landmarks"]["toe"]
  with self.assertRaisesRegex(ValueError,"MISSING_HEEL_OR_TOE"):validate_sole(s)
 def test_actual_ray_triangle_occlusion_mutant(self):
  # From the actual scene camera, one actor vertex is geometrically hidden
  # behind another actor's triangle halfway along the sight line.
  source={str(f):{ACTORS[0]:[(0.,0.,.75)],
      ACTORS[1]:[(-1.,-3.5,1.),(1.,-3.5,1.),(0.,-3.5,2.)]} for f in FRAMES}
  result=occlusion(source,{ACTORS[0]:[],ACTORS[1]:[(0,1,2)]})
  self.assertEqual(result["opposing_actor_occluded_vertex_count"][ACTORS[0]],7)
  self.assertEqual(result["ray_vertex_observations"],28)
 def test_unoccluded(self):
  source={str(f):{ACTORS[0]:[(-1.,0.,.75)],
      ACTORS[1]:[(1.,0.,.75),(1.1,0.,.75),(1.,.2,.75)]} for f in FRAMES}
  result=occlusion(source,{ACTORS[0]:[],ACTORS[1]:[(0,1,2)]})
  self.assertEqual(result["opposing_actor_occluded_vertex_count"][ACTORS[0]],0)
if __name__=="__main__":unittest.main()
