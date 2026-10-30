import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from mesh_checks import (actor_surface_clearance,verify_frames,camera_visible,point_triangle_distance,
 ray_triangle,ACTORS,FRAMES,GROUND_TOL)
def synthetic():
 verts_a=[(-1.,0.,.5),(-.8,0.,.5),(-1.,0.,.8)]
 verts_b=[(1.,0.,.5),(1.2,0.,.5),(1.,0.,.8)]
 return {"world_vertices":{str(f):{ACTORS[0]:[list(v) for v in verts_a],ACTORS[1]:[list(v) for v in verts_b]} for f in FRAMES}}
FACES={ACTORS[0]:[(0,1,2)],ACTORS[1]:[(0,1,2)]}
class Hostile(unittest.TestCase):
 def test_original_synthetic_positive(self):
  stats=verify_frames(synthetic(),FACES)
  self.assertGreater(stats["sampled_triangle_min_separation"],.025)
 def test_exact_ground_mutation(self):
  s=synthetic();s["world_vertices"]["12"][ACTORS[0]][0][2]=-GROUND_TOL-.001
  with self.assertRaisesRegex(ValueError,"GROUND_PENETRATION"):verify_frames(s,FACES)
 def test_source_teleport(self):
  s=synthetic()
  for v in s["world_vertices"]["12"][ACTORS[0]]:v[1]+=5 # teleport along view axis, still in frustum
  with self.assertRaisesRegex(ValueError,"TELEPORT"):verify_frames(s,FACES)
 def test_surface_collision(self):
  s=synthetic()
  for f in FRAMES:s["world_vertices"][str(f)][ACTORS[1]]=copy.deepcopy(s["world_vertices"][str(f)][ACTORS[0]])
  with self.assertRaisesRegex(ValueError,"COLLISION"):verify_frames(s,FACES)
 def test_camera_clipping(self):
  s=synthetic()
  for f in FRAMES:
   for v in s["world_vertices"][str(f)][ACTORS[1]]:v[0]+=100
  with self.assertRaisesRegex(ValueError,"OUTSIDE_CAMERA"):verify_frames(s,FACES)
 def test_triangle_distance_interior(self):
  d=point_triangle_distance((.1,.1,.2),(0.,0.,0.),(1.,0.,0.),(0.,1.,0.))
  self.assertAlmostEqual(d,.2,places=8)
 def test_triangle_edge_intersect(self):
  hit=ray_triangle((.2,.2,-1.),(0.,0.,2.),(0.,0.,0.),(1.,0.,0.),(0.,1.,0.))
  self.assertAlmostEqual(hit,.5,places=8)
 def test_behind_camera(self):
  self.assertFalse(camera_visible((0.,-100.,1.)))
 def test_forged_frame(self):
  s=synthetic();del s["world_vertices"]["24"]
  with self.assertRaises(KeyError):verify_frames(s,FACES)
if __name__=="__main__":unittest.main()
