"""R009 independent source-bound human-inspired motion gait hostile/offline tests."""
import copy,hashlib,json,math,os,struct,tempfile,unittest
from pathlib import Path
import gait_v2 as g

SOURCE=Path(os.environ.get('R009_GAIT_SOURCE','/mnt/data/r009-aster-juniper-original-heading-aligned-REVIEW.glb'))
SHA='837dbd91e5851072b7f4d5f31fdeb5517c19f85e913e829e5e488406f374f651'

class GaitV2Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.dir=Path(self.tmp.name);self.src=self.dir/'source.glb';self.src.write_bytes(SOURCE.read_bytes())
  self.out=self.dir/'derived.glb';self.rec=self.dir/'receipt.json'
  self.sha=SHA
 def produce(self):return g.produce(self.src,self.out,self.rec,self.sha)[0]
 def mutated(self,fn):
  d,bb=g.decode_glb(self.src.read_bytes());fn(d)
  self.src.write_bytes(g.encode_glb(d,bb));self.sha=hashlib.sha256(self.src.read_bytes()).hexdigest()
 def test_success_full_source_binding_and_not_human_accepted(self):
  r=self.produce();self.assertEqual(r['skins'],[17,17]);self.assertEqual(r['channels'],28)
  self.assertFalse(r['human_motion_accepted']);self.assertTrue(r['source_bytes_untouched'])
  self.assertEqual(hashlib.sha256(self.src.read_bytes()).hexdigest(),SHA)
 def test_no_rewrite_existing_source(self):
  with self.assertRaisesRegex(ValueError,'SOURCE_MUTATION_REFUSED'):g.produce(self.src,self.src,self.rec,SHA)
 def test_wrong_source_sha(self):
  self.sha='0'*64
  with self.assertRaisesRegex(ValueError,'SOURCE_HASH_MISMATCH'):self.produce()
  self.assertFalse(self.out.exists())
 def test_vendor_or_nonoriginal_fails_closed(self):
  self.mutated(lambda d:d['extras'].update(third_party_models=True))
  with self.assertRaisesRegex(ValueError,'NOT_OWNER_ORIGINAL'):self.produce()
 def test_skin_mismatch_denied(self):
  self.mutated(lambda d:d['skins'][0]['joints'].pop())
  with self.assertRaisesRegex(ValueError,'INCORRECT_RIG'):self.produce()
 def test_missing_joint_denied(self):
  self.mutated(lambda d:d['nodes'][6].update(name='NOT_OWN_HIP'))
  with self.assertRaisesRegex(ValueError,'MISSING_RIG_PART'):self.produce()
 def test_multiple_source_clips_denied(self):
  self.mutated(lambda d:d['animations'].append(copy.deepcopy(d['animations'][0])))
  with self.assertRaisesRegex(ValueError,'UNEXPECTED_CLIPS'):self.produce()
 def test_corrupt_header_denied(self):
  self.src.write_bytes(b'bad GLB');self.sha=hashlib.sha256(self.src.read_bytes()).hexdigest()
  with self.assertRaisesRegex(ValueError,'BAD_SOURCE_GLB'):self.produce()
 def test_nonphysical_kinematic_extension_denied(self):
  previous=g.T
  try:
   g.T=1.9
   with self.assertRaisesRegex(ValueError,'IK_UNREACHABLE'):self.produce()
  finally:g.T=previous
 def test_bilateral_phases_are_half_stride_apart(self):
  pose=g.frame_pose(6,0)
  self.assertAlmostEqual((pose['legs']['R']['phase']-pose['legs']['L']['phase'])%1,.5,places=6)
 def test_forward_landing_then_backward_trailing_foot(self):
  self.assertGreater(g.leg_target(0.)[0],.12)
  self.assertLess(g.leg_target(g.D)[0],-.20)
 def test_hip_lifts_knee_and_foot_in_swing(self):
  pose=g.frame_pose(0,0)
  max_knee=0;min_hip=1e9;max_hip=-1e9
  for frame in range(g.FRAMES):
   p=g.frame_pose(frame,0)
   for side in ('L','R'):
    k=p['legs'][side]['angles']['knee'];hip=p['legs'][side]['angles']['hip']
    max_knee=max(max_knee,-math.degrees(k));min_hip=min(min_hip,math.degrees(hip));max_hip=max(max_hip,math.degrees(hip))
  self.assertGreater(max_knee,55);self.assertLess(max_knee,70)
  self.assertLess(min_hip,-4);self.assertGreater(max_hip,24)
 def test_contralateral_arm_leg_and_real_elbow_motion(self):
  import numpy as np
  x=[];a=[];elbow=[]
  for frame in range(g.FRAMES):
   p=g.frame_pose(frame,0)
   x.append(p['legs']['L']['fwd']);a.append(p['arms']['R']['shoulder']);elbow.append(p['arms']['R']['elbow'])
  self.assertGreater(np.corrcoef(x,a)[0,1],.85)
  self.assertGreater(math.degrees(max(elbow)-min(elbow)),25)
 def test_pelvis_and_foot_motions_smooth_phase(self):
  for p in (0,g.D,.99999):
   ff,y,pitch,stage=g.leg_target(p)
   self.assertTrue(all(math.isfinite(q) for q in (ff,y,pitch)))
  self.assertAlmostEqual(g.leg_target(0)[0],g.leg_target(1-.000001)[0],delta=.0001)

if __name__=='__main__':unittest.main()
