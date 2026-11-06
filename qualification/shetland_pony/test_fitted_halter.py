"""Hostile non-Blender fit and shape tests for the equine muzzle/halter candidate."""
import math
import unittest
from equine_sculpt import HEAD, sweep
from fitted_halter import nose_loop, cheek_path, crown_loop, throat_loop, strap_surface

class MuzzleAndHalterTests(unittest.TestCase):
    def test_muzzle_not_overlong_or_drooping(self):
        self.assertGreaterEqual(len(HEAD),8)
        self.assertLessEqual(HEAD[-1][0]-HEAD[0][0],.54)
        self.assertGreaterEqual(HEAD[-1][1],.85)
        self.assertGreaterEqual(HEAD[-1][2],.105)
        self.assertLess(HEAD[-1][2],HEAD[1][2])
        self.assertTrue(all(HEAD[i+1][0]>HEAD[i][0] for i in range(len(HEAD)-1)))

    def test_head_closed_topology(self):
        vertices,faces=sweep(HEAD)
        self.assertGreater(len(vertices),500)
        self.assertGreater(len(faces),800)
        self.assertTrue(all(math.isfinite(v) for p in vertices for v in p))

    def test_noseband_closed_and_bilateral(self):
        ring=nose_loop()
        self.assertEqual(len(ring),64)
        self.assertAlmostEqual(max(p[1] for p in ring),-min(p[1] for p in ring),places=6)
        vertices,faces=strap_surface(ring,closed=True)
        self.assertEqual(len(vertices),128)
        self.assertEqual(len(faces),256)
        self.assertTrue(all(math.isfinite(x) for p in vertices for x in p))

    def test_anatomical_noseband_tilt_and_connected_cheek_hardware(self):
        ring=nose_loop()
        self.assertGreater(max(p[0] for p in ring)-min(p[0] for p in ring),.035)
        self.assertLess(max(p[0] for p in ring)-min(p[0] for p in ring),.055)
        self.assertAlmostEqual(ring[0][0],ring[32][0],places=8)
        self.assertAlmostEqual(ring[0][2],ring[32][2],places=8)
        left,right=cheek_path("L"),cheek_path("R")
        self.assertEqual(tuple(right[0]),tuple(ring[0]))
        for i in range(3):
            self.assertAlmostEqual(left[0][i],ring[32][i],places=8)
        crown=crown_loop()
        for i in range(3):
            self.assertAlmostEqual(right[-1][i],crown[0][i],places=8)
            self.assertAlmostEqual(left[-1][i],crown[-1][i],places=8)
        throat=throat_loop()
        self.assertLess(min(z for _,_,z in throat),.95)
        self.assertGreater(min(z for _,_,z in throat),.92)
        self.assertTrue(all(math.isfinite(v) for p in throat for v in p))

    def test_continuity_and_symmetry(self):
        a=cheek_path("L");b=cheek_path("R")
        self.assertEqual(len(a),len(b))
        for left,right in zip(a,b):
            self.assertAlmostEqual(left[0],right[0])
            self.assertAlmostEqual(left[1],-right[1])
            self.assertAlmostEqual(left[2],right[2])
        self.assertEqual(len(crown_loop()),32)
        self.assertEqual(len(throat_loop()),24)
        for path in (a,b,crown_loop(),throat_loop()):
            verts,faces=strap_surface(path)
            self.assertEqual(len(verts),len(path)*2)
            self.assertEqual(len(faces),(len(path)-1)*4)

    def test_hostile_inputs(self):
        for fn,args in ((nose_loop,(5,)),(cheek_path,("X",)),(crown_loop,(4,)),(throat_loop,(4,))):
            with self.assertRaises(ValueError):fn(*args)
        with self.assertRaises(ValueError):strap_surface([(0,0,0),(1,1,1)])
        with self.assertRaises(ValueError):strap_surface(nose_loop(),width=-1)

if __name__=="__main__":unittest.main()
