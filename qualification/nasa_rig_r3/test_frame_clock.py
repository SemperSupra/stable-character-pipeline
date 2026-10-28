import unittest
from frame_clock import source_aligned_frames

class SourceTimeOrigin(unittest.TestCase):
    def test_nasa_source_zero_to_nine_seconds(self):
        self.assertEqual(source_aligned_frames(10,24),list(range(0,217,24)))
        self.assertEqual(source_aligned_frames(10,30),list(range(0,271,30)))
    def test_original_bug_is_detectable(self):
        expected=source_aligned_frames(10,24)
        faulty=[1+i*24 for i in range(10)]
        self.assertNotEqual(faulty,expected)
        self.assertEqual([f-e for f,e in zip(faulty,expected)],[1]*10)
    def test_fractional_frame_rate(self):
        s=source_aligned_frames(10,30000/1001)
        self.assertEqual(s[0],0)
        self.assertTrue(all(b>a for a,b in zip(s,s[1:])))
    def test_bad_frame_rate(self):
        for x in [0, -1, float("nan"),float("inf"),241,True]:
            with self.subTest(x=x),self.assertRaises(ValueError):
                source_aligned_frames(10,x)
    def test_bad_sample_count(self):
        for x in [0,1,31,True,10.0]:
            with self.subTest(x=x),self.assertRaises(ValueError):
                source_aligned_frames(x,24)
if __name__=="__main__":unittest.main()
