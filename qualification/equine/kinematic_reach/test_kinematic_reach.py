import importlib.util,math,pathlib,unittest
p=pathlib.Path(__file__).with_name('kinematic_reach.py')
s=importlib.util.spec_from_file_location('kinematic_reach',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class KinematicReachTests(unittest.TestCase):
 def fixture(self):
  specs={};targets={}
  for name in m.HORSE_FOOT_NAMES:
   x=.4 if name.startswith('front') else -.48
   hip=.81 if name.startswith('front') else .78
   if name.startswith('front'):
    specs[name]=[((x,0,hip),(x+.012,0,.612)),((x+.012,0,.612),(x-.006,0,.432)),((x-.006,0,.432),(x+.012,0,.26))]
   else:
    specs[name]=[((x,0,hip),(x+.06,0,.610)),((x+.06,0,.610),(x-.078,0,.432)),((x-.078,0,.432),(x+.012,0,.26))]
   t=[]
   for frame in range(1,m.FRAME_COUNT+1):
    rel=.08;root=.16*(frame-1)/m.FRAME_COUNT
    t.append((frame,root,(x+root+rel,0,.252)))
   targets[name]=t
  return specs,targets
 def test_realistic_original_3_link_travel_limit(self):
  specs,targets=self.fixture();r=m.reachability(specs,targets)
  self.assertEqual(r['front_L']['infeasible_frame_count'],48)
  self.assertEqual(r['hind_L']['infeasible_frame_count'],0)
 def test_small_reversible_carpus_candidate_reaches_but_is_not_anatomical_certification(self):
  specs,targets=self.fixture();r=m.reachability(specs,targets,carpus_shift=.04)
  self.assertEqual(r['front_R']['infeasible_frame_count'],0)
 def test_broken_joint_chain_refused(self):
  s,t=self.fixture();s['front_L'][1]=((100,0,0),s['front_L'][1][1])
  with self.assertRaises(ValueError):m.reachability(s,t)
 def test_missing_frame_refused(self):
  s,t=self.fixture();t['front_R']=t['front_R'][:-1]
  with self.assertRaises(ValueError):m.reachability(s,t)
 def test_unbounded_candidate_refused(self):
  s,t=self.fixture()
  for bad in [-1,float('nan'),float('inf'),.07]:
   with self.assertRaises(ValueError):m.reachability(s,t,carpus_shift=bad)
 def test_duplicate_source_frame_refused(self):
  s,t=self.fixture();t['hind_L'][0]=t['hind_L'][1]
  with self.assertRaises(ValueError):m.reachability(s,t)
if __name__=='__main__':unittest.main()
