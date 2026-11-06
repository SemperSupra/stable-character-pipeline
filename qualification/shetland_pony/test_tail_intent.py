import unittest
from tail_intent import FRAMES,TAIL_BONES,LIMIT_RAD,SNAP_LIMIT,sample,timeline,validate_timeline

class TailTests(unittest.TestCase):
    def test_deterministic_and_bounded(self):
        t=timeline()["frames"];self.assertEqual(len(t),FRAMES)
        self.assertTrue(validate_timeline(t))
        self.assertEqual(t,[sample(i) for i in range(1,FRAMES+1)])
        self.assertEqual(set(t[0]),set(TAIL_BONES))
        self.assertTrue(any(abs(p["tail_1"])>.05 for p in t))
        self.assertTrue(any(abs(p["tail_3"])>.09 for p in t))
        self.assertTrue(all(abs(v)<=LIMIT_RAD for p in t for v in p.values()))
    def test_delayed_follow_through(self):
        t=timeline()["frames"]
        peaks=[max(range(FRAMES),key=lambda j:abs(t[j][b])) for b in TAIL_BONES]
        self.assertLess(peaks[0],peaks[1]);self.assertLess(peaks[1],peaks[2])
        self.assertEqual(t[0],{"tail_1":0.,"tail_2":0.,"tail_3":0.})
        self.assertEqual(t[-1],{"tail_1":0.,"tail_2":0.,"tail_3":0.})
    def test_disable_and_hostile_cases(self):
        for f in range(1,FRAMES+1):self.assertTrue(all(x==0 for x in sample(f,False).values()))
        for x in (0,49,None,2.5,True):
            with self.assertRaises(ValueError):sample(x)
        with self.assertRaises(ValueError):sample(1,"off")
        bad=timeline()["frames"];bad[4]["tail_2"]=2.0
        with self.assertRaises(ValueError):validate_timeline(bad)
        bad=timeline()["frames"];bad[4]["tail_3"]=.58;bad[5]["tail_3"]=-.58
        with self.assertRaises(ValueError):validate_timeline(bad)

if __name__=="__main__":unittest.main()
