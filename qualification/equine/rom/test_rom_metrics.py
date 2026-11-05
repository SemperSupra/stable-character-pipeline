import math,unittest
from rom_metrics import evaluate_triplet,evaluate,FEET,ANATOMY_MISSING

def fixture(missing_stifle=False):
    bones={"hind_L_stifle","hind_R_stifle"}
    if missing_stifle:bones=set()
    trajectories={}
    for foot in FEET:
        traj=[]
        for frame in range(1,49):
            # ~10 deg at center, oscillatory flexion, constant bone lengths.
            angle=.10+.12*math.sin((frame-1)*2*math.pi/48)
            a=(0,0,1)
            j=(0,0,.65)
            b=(.25*math.sin(angle),0,.65-.25*math.cos(angle))
            traj.append({"frame":frame,"proximal":a,"joint":j,"distal":b})
        trajectories[foot]=traj
    return trajectories,bones
class ROM(unittest.TestCase):
    def test_straight(self):
        self.assertAlmostEqual(evaluate_triplet((0,0,1),(0,0,.5),(0,0,0))["flexion_deg"],0)
    def test_valid_engineering_fixture(self):
        t,b=fixture()
        self.assertEqual(evaluate(t,b)["scientific_verdict"],"GUARDRAIL_NO_FAILURE_BIOLOGICAL_UNKNOWN")
    def test_missing_stifle_always_fails(self):
        t,b=fixture(True)
        r=evaluate(t,b)
        self.assertEqual(r["scientific_verdict"],"JOINT_KINEMATICS_OR_ANATOMY_FAIL")
        self.assertEqual(sum(x.startswith("ANATOMICAL_MISSING") for x in r["failure_codes"]),2)
    def test_immobile_knee(self):
        t,b=fixture()
        for foot in FEET:
            t[foot]=[dict(t[foot][0],frame=i) for i in range(1,49)]
        self.assertIn("front_L:immobile_knee_or_hock",evaluate(t,b)["failure_codes"])
    def test_discontinuous(self):
        t,b=fixture();t["hind_L"][4]["frame"]=100
        with self.assertRaises(ValueError):evaluate(t,b)
    def test_lateral_drift(self):
        t,b=fixture()
        t["front_L"][10]["joint"]=(0,.12,.65)
        self.assertIn("front_L:transverse_plane_deviation",evaluate(t,b)["failure_codes"])
    def test_nan(self):
        with self.assertRaises(ValueError):
            evaluate_triplet((0,0,float("nan")),(0,0,.5),(0,0,0))
if __name__=="__main__":unittest.main()
