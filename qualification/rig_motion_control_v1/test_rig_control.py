"""Adversarial source-only tests; do not falsely claim native Blender qualification."""
import unittest,math
from rig_control import (Stance,plan_foot_targets,solve_two_bone,audit_contact_kinematics,norm,sub)

class TestIK(unittest.TestCase):
    def test_solve_multiple_planes_and_mirrored_bend(self):
        cases=[((0,0,1),(0,0,.1),(.3,0,.5)),
               ((0,0,1),(0,0,.1),(-.3,0,.5)),
               ((0,0,1),(0,.2,.1),(.2,.3,.5)),
               ((0,0,0),(.75,.25,.1),(.25,0,.4))]
        for origin,ankle,pole in cases:
            with self.subTest(origin=origin,pole=pole):
                r=solve_two_bone(origin,ankle,pole,.55,.55)
                self.assertLess(r['residual_m'],1e-8)
                self.assertFalse(r['native_bone_pose_verified'])
                self.assertFalse(r['skin_deformation_verified'])
        a=solve_two_bone((0,0,1),(0,0,.1),(.3,0,.5),.55,.55)['joint']
        b=solve_two_bone((0,0,1),(0,0,.1),(-.3,0,.5),.55,.55)['joint']
        self.assertGreater(a[0],0);self.assertLess(b[0],0)
    def test_reach_boundary_straight(self):
        r=solve_two_bone((0,0,0),(1.1,0,0),(0,1,0),.55,.55)
        self.assertLess(norm(sub(r['joint'],(.55,0,0))),1e-7)
    def test_reject_unreachable_and_coincident(self):
        for target in ((1.5,0,0),(0,0,0)):
            with self.subTest(target=target):
                with self.assertRaisesRegex(ValueError,"UNREACHABLE_CHAIN_TARGET|COINCIDENT_CHAIN_ENDPOINTS"):
                    solve_two_bone((0,0,0),target,(0,1,0),.5,.5)
    def test_reject_ambiguous_pole(self):
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS_BEND_POLE"):
            solve_two_bone((0,0,0),(1,0,0),(2,0,0),.7,.7)
    def test_reject_nonfinite_bool_and_bad_lengths(self):
        for v in (math.nan,math.inf,True,-.1,0):
            with self.subTest(v=v):
                with self.assertRaisesRegex(ValueError,"INVALID_SEGMENT_LENGTHS"):
                    solve_two_bone((0,0,0),(0,0,.7),(0,1,0),v,.7)
        for v in (math.nan,math.inf,True,'0'):
            with self.subTest(target=v):
                with self.assertRaisesRegex(ValueError,"INVALID_TARGET"):
                    solve_two_bone((0,0,0),(v,0,.2),(0,1,0),.55,.55)

class TestStance(unittest.TestCase):
    def test_72_frame_explicit_stance_lock_and_swing(self):
        bouts=[Stance(0,11,(0,0,0)),Stance(24,35,(.7,0,0)),
               Stance(48,59,(1.4,0,0)),Stance(69,71,(2.05,0,0))]
        frames=plan_foot_targets(72,bouts)
        self.assertEqual(len(frames),72)
        for b in bouts:
            self.assertEqual(set(tuple(frames[f]['target']) for f in range(b.start,b.end+1)),{b.anchor})
            self.assertTrue(all(frames[f]['mode']=='STANCE' for f in range(b.start,b.end+1)))
        for f in (14,17,40,64):
            self.assertEqual(frames[f]['mode'],'SWING')
            self.assertGreater(frames[f]['target'][2],0)
        self.assertFalse(any(f['contact_certified'] for f in frames))
        # Horizontal position must not jump at stance/swing transition.
        self.assertLess(max(norm(sub(a['target'],b['target'])) for a,b in zip(frames,frames[1:])),.20)
    def test_pre_post_not_marked_as_contact(self):
        a=plan_foot_targets(12,[Stance(3,6,(0,0,0))])
        self.assertEqual([f['mode'] for f in a],['PRE']*3+['STANCE']*4+['POST']*5)
    def test_reject_clock_order_overlap_and_data(self):
        for clock,bouts,error in [
            (72,[],"MISSING_STANCE_BOUTS"),
            (72,[Stance(11,10,(0,0,0))],"INVALID_STANCE_CLOCK"),
            (72,[Stance(20,25,(0,0,0)),Stance(0,5,(1,0,0))],"UNSORTED_STANCE_BOUTS"),
            (72,[Stance(0,10,(0,0,0)),Stance(11,20,(1,0,0))],"NO_SWING_INTERVAL"),
            (72,[Stance(0,10,(math.inf,0,0))],"INVALID_STANCE_ANCHOR"),
            (True,[Stance(0,1,(0,0,0))],"INVALID_FRAME_COUNT")]:
            with self.subTest(error=error):
                with self.assertRaisesRegex(ValueError,error):plan_foot_targets(clock,bouts)
    def test_stance_exact_no_slide_for_controller_not_skin(self):
        x=plan_foot_targets(72,[Stance(0,15,(0,0,0)),Stance(28,45,(.7,0,0)),Stance(58,71,(1.45,0,0))])
        for i in range(71):
            if x[i]['mode']==x[i+1]['mode']=='STANCE':
                self.assertEqual(norm(sub(x[i]['target'],x[i+1]['target'])),0)

class TestTwoFootContract(unittest.TestCase):
    def test_two_legs_72f_reproducible_and_residual(self):
        left=plan_foot_targets(72,[Stance(0,11,(0,.14,.02)),Stance(24,35,(.68,.14,.02)),
                                    Stance(48,59,(1.4,.14,.02)),Stance(69,71,(2.05,.14,.02))])
        right=plan_foot_targets(72,[Stance(0,3,(0,-.14,.02)),Stance(16,27,(.44,-.14,.02)),
                                     Stance(40,51,(1.12,-.14,.02)),Stance(64,71,(1.88,-.14,.02))])
        roots=[2.05*f/71 for f in range(72)]
        hl=[(root,.14,.92) for root in roots];hr=[(root,-.14,.92) for root in roots]
        pl=[(root+.5,.14,.50) for root in roots];pr=[(root+.5,-.14,.50) for root in roots]
        result=audit_contact_kinematics(left,right,hl,hr,(.55,.55),pl,pr)
        self.assertEqual(result['frames'],72)
        self.assertFalse(result['mvp_accepted'])
        self.assertEqual(result['native_80_bone_skin_verification'],'NOT_RUN')
        for side in ('L','R'):
            self.assertEqual(len(result['by_side'][side]),72)
            self.assertLess(max(z['residual_m'] for z in result['by_side'][side]),1e-8)
    def test_clock_mismatch_fails_closed(self):
        left=plan_foot_targets(72,[Stance(0,71,(0,0,0))]);right=left[:-1]
        with self.assertRaisesRegex(ValueError,'MISALIGNED_MOTION_CLOCKS'):
            audit_contact_kinematics(left,right,[(0,0,1)]*72,[(0,0,1)]*72,(.55,.55),[(0,1,.5)]*72,[(0,1,.5)]*72)

if __name__=='__main__':unittest.main()
