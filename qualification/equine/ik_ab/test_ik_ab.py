import json, tempfile, unittest
from pathlib import Path
from patch_candidate import patch, ORIGINAL, PATCHED
from compare_ab import compare, side_report, read_json

class ABTests(unittest.TestCase):
 def test_reversible_exact_source_not_inplace(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'original.py';q=Path(d)/'candidate.py'
   p.write_text('a=1\n'+ORIGINAL+'\nb=2\n')
   result=patch(p,q)
   self.assertIn(PATCHED,q.read_text());self.assertIn(ORIGINAL,p.read_text())
   self.assertEqual(q.read_text().replace(PATCHED,ORIGINAL),p.read_text())
   self.assertFalse(result['owner_source_modified'])
   with self.assertRaises(ValueError):patch(p,p)
   with self.assertRaises(ValueError):patch(p,q)
 def test_broken_source_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'a';b=Path(d)/'b'
   for data in ('',ORIGINAL+ORIGINAL,PATCHED,'carpus=(x-.01,y,.432)'):
    a.write_text(data)
    with self.assertRaises(ValueError):patch(a,b)
 def science(self,front_skate=2,front_swing=0,hind_skate=0):
  f={}
  for n in ('front_L_hoof','front_R_hoof','hind_L_hoof','hind_R_hoof'):
   front=n.startswith('front')
   f[n]={'skate_pairs_over_3cm':front_skate//2 if front else hind_skate//2,
     'max_near_ground_displacement_m':.035 if front_skate else .012,
     'max_ground_penetration_m':0,'frames_above_swing_clearance':front_swing if front else 8}
  return {'schema':'equine.foot.science.v1','frames':48,'source':'native_evaluated_skin_mesh','feet':f}
 def rom(self,codes=()):
  return {'schema':'equine.rom.actual-three-segment.v1','observed_frames':48,'joint_reports':{n:{} for n in ('front_L','front_R','hind_L','hind_R')},'failure_codes':list(codes)}
 def reach(self,n):
  return {'schema':'equine.ik.reachability-hypothesis.v1','baseline':{'front_L':{'infeasible_frame_count':n},'front_R':{'infeasible_frame_count':n}}}
 def test_candidate_earned_by_actual_geometry_not_reach_only(self):
  normal=self.science()
  passcase=self.science(0,4)
  good=compare(normal,passcase,self.rom(),self.rom(),self.reach(34),self.reach(0),'a'*64,'b'*64)
  self.assertEqual(good['outcome'],'CANDIDATE_PROXY_IMPROVEMENT_NOT_ACCEPTED')
  weak=compare(normal,normal,self.rom(),self.rom(),self.reach(34),self.reach(0),'a'*64,'b'*64)
  self.assertEqual(weak['outcome'],'REJECT_OR_INCONCLUSIVE_CANDIDATE')
 def test_new_rom_failure_rejects_improvement(self):
  r=compare(self.science(),self.science(0,4),self.rom(),self.rom(('front_L:overflexion',)),
           self.reach(34),self.reach(0),'a'*64,'b'*64)
  self.assertEqual(r['outcome'],'REJECT_OR_INCONCLUSIVE_CANDIDATE')
 def test_hind_regression_rejects(self):
  r=compare(self.science(),self.science(0,4,2),self.rom(),self.rom(),self.reach(34),self.reach(0),'a'*64,'b'*64)
  self.assertEqual(r['outcome'],'REJECT_OR_INCONCLUSIVE_CANDIDATE')
 def test_missing_or_forged_evidence_rejected(self):
  x=self.science();del x['feet']['hind_L_hoof']
  with self.assertRaises(ValueError):side_report(x)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.json';p.write_text('{"a":1,"a":2}')
   with self.assertRaises(ValueError):read_json(p)
 def test_same_glb_cannot_be_an_ab(self):
  with self.assertRaises(ValueError):compare(self.science(),self.science(),self.rom(),self.rom(),self.reach(34),self.reach(0),'a'*64,'a'*64)

 def test_ground_penetration_regression_never_earns_improvement(self):
  baseline=self.science()
  candidate=self.science(0,4)
  candidate['feet']['front_L_hoof']['max_ground_penetration_m']=.00749
  result=compare(baseline,candidate,self.rom(),self.rom(),self.reach(34),self.reach(0),'a'*64,'b'*64)
  self.assertEqual(result['outcome'],'REJECT_OR_INCONCLUSIVE_CANDIDATE')
  self.assertEqual(result['new_ground_penetration_regressions'],['front_L_hoof'])
 def test_noninteger_and_impossible_event_counts_are_rejected(self):
  for key,bad in (('skate_pairs_over_3cm',True),
                  ('skate_pairs_over_3cm',.5),
                  ('skate_pairs_over_3cm',48),
                  ('frames_above_swing_clearance',49),
                  ('frames_above_swing_clearance',False)):
   with self.subTest(key=key,value=bad):
    evidence=self.science()
    evidence['feet']['front_L_hoof'][key]=bad
    with self.assertRaises(ValueError):side_report(evidence)

if __name__=='__main__':unittest.main()
