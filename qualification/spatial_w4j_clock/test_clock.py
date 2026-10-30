import unittest
from clock import Clock,RIGHTS,MAX_TICK,reject_collapse,packet
class TestRational(unittest.TestCase):
 def test_12_fps_walk(self):
  c=Clock(12,1)
  self.assertEqual(c.frame(4000),1)
  self.assertEqual(c.frame(16000),4)
  self.assertEqual(c.start(4),16000)
 def test_source_24_video(self):
  c=Clock(24,1)
  self.assertEqual(c.frame(2000),1)
  self.assertEqual(c.start(47),94000)
 def test_ntsc_fractional_boundaries(self):
  c=Clock(30000,1001)
  for f in (0,1,2,100,997,29970):
   s=c.start(f)
   self.assertEqual(c.frame(s),f)
   if f>0:self.assertLess(c.frame(s-1),f)
 def test_no_high_tick_float_collapse(self):
  a=1<<60;b=a+1
  self.assertEqual(float(a),float(b))
  r=reject_collapse(a,b,Clock(30000,1001))
  self.assertEqual(r["source_sample_delta"],1)
  self.assertTrue(r["strict_source_order"])
 def test_all_clock_grid_exact(self):
  for num,den in [(12,1),(24,1),(30,1),(30000,1001)]:
   c=Clock(num,den)
   for f in range(0,400):
    s=c.start(f)
    self.assertEqual(c.frame(s),f)
 def test_order_and_rights(self):
  r=packet(Clock(12,1),[{"sample":4000,"rights":RIGHTS,"kind":"SOURCE_ANNOTATED_EVENT"},{"sample":16000,"rights":RIGHTS,"kind":"SOURCE_ANNOTATED_EVENT"}])
  self.assertEqual([x["frame"] for x in r],[1,4])
 def test_rejections(self):
  bad=[
   lambda: Clock(25,1).frame(4000),
   lambda: Clock(12,1,44100).frame(4000),
   lambda: Clock(12,1,rights="INFERRED").frame(4000),
   lambda: Clock(12,1).frame(-1),
   lambda: Clock(12,1).frame(MAX_TICK+1),
   lambda: Clock(12,1).frame(1.5),
   lambda: Clock(12,1).start(-1),
   lambda: reject_collapse(100,100,Clock(12,1)),
   lambda: reject_collapse(101,100,Clock(12,1)),
   lambda: packet(Clock(12,1),[{"sample":4000,"rights":RIGHTS,"kind":"SOURCE_ANNOTATED_EVENT"},{"sample":4000,"rights":RIGHTS,"kind":"SOURCE_ANNOTATED_EVENT"}]),
   lambda: packet(Clock(12,1),[{"sample":100,"rights":"UNKNOWN","kind":"SOURCE_ANNOTATED_EVENT"}]),
   lambda: packet(Clock(12,1),[{"sample":100,"rights":RIGHTS,"kind":"INFERRED_EVENT"}]),
  ]
  for f in bad:
   with self.subTest(index=bad.index(f)),self.assertRaises(ValueError):f()
if __name__=="__main__":unittest.main()
