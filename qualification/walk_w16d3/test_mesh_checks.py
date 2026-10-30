import copy,sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from mesh_checks import verify_frames,swept_vertex_minimum,FRAMES,ACTORS,NEAR_SURFACE,GROUND_TOL
FACES={a:[(0,1,2),(28,29,30)] for a in ACTORS}
def source():
 result={"world_vertices":{}}
 for f in FRAMES:
  row={}
  for idx,name in enumerate(ACTORS):
   center=-1.5 if idx==0 else 1.5
   row[name]=[[center+(k%7)*.005,((k//7)%2)*.01,.35+(k%7)*.03] for k in range(56)]
  result["world_vertices"][str(f)]=row
 return result
class Negative(unittest.TestCase):
 def test_source_only_clean(self):
  s=source();r=verify_frames(s,FACES)
  self.assertGreater(r["sampled_triangle_min_separation"],NEAR_SURFACE)
  self.assertGreater(r["swept_linear_vertex_track_minimum"],NEAR_SURFACE)
  self.assertEqual(len(r["procedural_leg_submesh_min_z"]),2)
 def test_ground_rejects(self):
  s=source();s["world_vertices"]["0"][ACTORS[0]][0][2]=-.002
  with self.assertRaisesRegex(ValueError,"GROUND_PENETRATION"):verify_frames(s,FACES)
 def test_static_surface_rejects(self):
  s=source()
  s["world_vertices"]["0"][ACTORS[1]]=copy.deepcopy(s["world_vertices"]["0"][ACTORS[0]])
  with self.assertRaisesRegex(ValueError,"SAMPLED_TRIANGLE_SURFACE_COLLISION"):verify_frames(s,FACES)
 def test_swept_crosses_without_endpoint_collisions(self):
  s=source();s["world_vertices"]["12"][ACTORS[0]]=copy.deepcopy(s["world_vertices"]["0"][ACTORS[1]])
  s["world_vertices"]["12"][ACTORS[1]]=copy.deepcopy(s["world_vertices"]["0"][ACTORS[0]])
  with self.assertRaisesRegex(ValueError,"SWEPT_VERTEX_TRACK_COLLISION"):verify_frames(s,FACES)
 def test_swept_identical(self):
  a=[[0.,0.,1.]]
  b=[[0.,0.,1.]]
  self.assertEqual(swept_vertex_minimum(a,a,b,b),0.)
 def test_mismatched_vertex_track_rejects(self):
  with self.assertRaisesRegex(ValueError,"INDEX_TRACK_DISCONTINUITY"):
   swept_vertex_minimum([[0.,0.,1.]],[],[[1.,0.,1.]],[[1.,0.,1.]])
 def test_camera_rejects(self):
  s=source()
  for f in FRAMES:
   for v in s["world_vertices"][str(f)][ACTORS[0]]:v[0]+=100
  with self.assertRaisesRegex(ValueError,"OUTSIDE_CAMERA_PROXY"):verify_frames(s,FACES)
 def test_teleport_in_view_axis(self):
  s=source()
  for v in s["world_vertices"]["12"][ACTORS[0]]:v[1]+=5
  with self.assertRaisesRegex(ValueError,"TELEPORT"):verify_frames(s,FACES)
if __name__=="__main__":unittest.main()
