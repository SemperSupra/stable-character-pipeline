import unittest,math
from angle_filter import smooth_euler_cycle,circular_mean
class Filter(unittest.TestCase):
    def test_constant_rotation_unchanged(self):
        arr=[(.1,-.2,.3)]*48
        result=smooth_euler_cycle(arr)
        self.assertEqual(len(result),48)
        self.assertTrue(all(abs(x-y)<1e-9 for a,b in zip(result,arr) for x,y in zip(a,b)))
    def test_suppress_source_step(self):
        arr=[(.0,0,0)]*48
        arr[10:43]=[(math.radians(23.27),0,0)]*33
        result=smooth_euler_cycle(arr)
        diffs=[abs(result[(i+1)%48][0]-result[i][0]) for i in range(48)]
        self.assertLess(max(diffs),math.radians(14))
    def test_wraparound_preserved(self):
        vals=[math.radians(x) for x in (178,179,-179,-178,179)]
        result=circular_mean(vals)
        self.assertLess(abs(abs(result)-math.pi),.08)
    def test_bad_inputs(self):
        with self.assertRaises(ValueError):smooth_euler_cycle([(0,0,0)]*2)
        with self.assertRaises(ValueError):smooth_euler_cycle([(math.nan,0,0)]*48)
if __name__=="__main__":unittest.main()
