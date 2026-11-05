import unittest
from footpaths import (CYCLE_FRAMES,FOOT_CONTACT_PHASE,REST_LOWER_TAIL_X,
                       STRIDE_M,SWING_HEIGHT_M,DUTY_FACTOR,target,trajectory)

class TestFootpath(unittest.TestCase):
    def test_all_four_with_stance_and_swing(self):
        data=trajectory()
        self.assertEqual(set(data),set(FOOT_CONTACT_PHASE))
        for foot,frames in data.items():
            self.assertEqual(len(frames),48)
            states={p.state for p in frames}
            self.assertEqual(states,{"stance_planned","swing_planned"})
            self.assertGreater(max(p.ankle_z for p in frames)-min(p.ankle_z for p in frames),.085)
    def test_stance_world_anchor_nearly_fixed(self):
        for foot,frames in trajectory().items():
            for a,b in zip(frames,frames[1:]):
                if a.state=="stance_planned" and b.state=="stance_planned" and b.phase>a.phase:
                    self.assertAlmostEqual(a.ankle_x,b.ankle_x,places=9)
    def test_phase_order(self):
        seen=[]
        for frame in range(1,49):
            for foot in FOOT_CONTACT_PHASE:
                p=target(frame,foot)
                if p.phase==0.0:
                    seen.append((frame,foot))
        self.assertEqual(seen,[(1,"hind_L"),(13,"front_L"),(25,"hind_R"),(37,"front_R")])
    def test_toe_clearance(self):
        data=trajectory()
        for foot,frames in data.items():
            self.assertGreaterEqual(max(p.ankle_z for p in frames),.350)
    def test_no_bad_input(self):
        for foot,frame in [("unseen",1),("hind_L",0),("hind_L",49)]:
            with self.assertRaises(ValueError):
                target(frame,foot)
    def test_clock_and_stride(self):
        self.assertAlmostEqual(target(1,"hind_L").root_x,0)
        self.assertAlmostEqual(target(48,"hind_L").root_x,STRIDE_M*47/CYCLE_FRAMES)
        self.assertEqual(CYCLE_FRAMES,48)
if __name__=="__main__": unittest.main()
