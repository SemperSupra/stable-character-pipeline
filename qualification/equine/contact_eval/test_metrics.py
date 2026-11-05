import unittest
from metrics import FEET,evaluate

def synthetic(step=.0,z=.0,frames=48):
    return {foot:[{"frame":frame+1,"x":frame*step,"y":0.0,"min_z":z}
                  for frame in range(frames)] for foot in FEET}

class TestContactMetrics(unittest.TestCase):
    def test_stance(self):
        d=evaluate(synthetic())
        self.assertEqual(d["scientific_verdict"],"NO_FAILURE_DETECTED_CONTACT_STILL_UNKNOWN")
        self.assertEqual(d["total_skate_pairs_over_threshold"],0)
    def test_skate(self):
        d=evaluate(synthetic(step=.1))
        self.assertEqual(d["scientific_verdict"],"FOOT_CONTACT_PROXY_FAIL")
        self.assertEqual(d["total_skate_pairs_over_threshold"],4*47)
    def test_penetration(self):
        d=evaluate(synthetic(z=-.045))
        self.assertEqual(d["scientific_verdict"],"FOOT_CONTACT_PROXY_FAIL")
        self.assertGreater(d["maximum_ground_penetration_m"],.015)
    def test_missing_hoof(self):
        d=synthetic()
        del d["hind_R_hoof"]
        with self.assertRaises(ValueError):evaluate(d)
    def test_sparse_frames(self):
        with self.assertRaises(ValueError):evaluate(synthetic(frames=3))
    def test_discontinuous(self):
        d=synthetic()
        d["front_R_hoof"][17]["frame"]=100
        with self.assertRaises(ValueError):evaluate(d)
    def test_unknown_even_when_green(self):
        d=evaluate(synthetic(z=.2))
        self.assertIn("UNKNOWN",d["scientific_verdict"])
if __name__ == "__main__":
    unittest.main()
