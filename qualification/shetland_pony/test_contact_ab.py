import unittest
from contact_ab import FEET, GROUND, measure, compare

def make(sole_min=.003,sole_peak=.12):
    points=[]
    for f in range(1,49):
        # 18 frames of swing, 30 planned stance: synthetic fixture ONLY
        z=(sole_peak if f<=18 else sole_min)
        points.append({"frame":f,"min_z":z,"x":0.0,"y":0.0})
    return {"schema":"equine.foot.science.v1","evaluated_hoof_trajectories":{n:[p.copy() for p in points] for n in FEET}}
class TestContactAB(unittest.TestCase):
    def test_calibration_fixture(self):
        d=compare(make(),make(sole_min=-.015,sole_peak=.102))
        self.assertTrue(all(d["gates"].values()))
        self.assertEqual(d["biomechanics"],"UNKNOWN")
    def test_no_improvement(self):
        self.assertEqual(compare(make(),make())["science_verdict"],"PROXY_HOOF_CALIBRATION_NOT_ACCEPTED")
    def test_no_swing(self):
        x=compare(make(),make(sole_min=-.015,sole_peak=-.015))
        self.assertFalse(x["gates"]["preserved_swing"])
    def test_deep_penetration(self):
        x=compare(make(),make(sole_min=-.04,sole_peak=.13))
        self.assertFalse(x["gates"]["no_deep_penetration"])
    def test_missing_foot(self):
        x=make();del x["evaluated_hoof_trajectories"]["front_L_hoof"]
        with self.assertRaises(ValueError):measure(x)
    def test_nan(self):
        x=make();x["evaluated_hoof_trajectories"]["front_L_hoof"][2]["min_z"]=float("nan")
        with self.assertRaises(ValueError):measure(x)
if __name__=="__main__":unittest.main()
