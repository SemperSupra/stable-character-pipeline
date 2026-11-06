import unittest,collections,math
from equine_sculpt import HEAD,NECK,sweep,leg
def manifold(faces):
    edges=collections.Counter()
    for tri in faces:
        if len(set(tri))!=3:raise AssertionError("degenerate")
        for a,b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
            edges[tuple(sorted((a,b)))] +=1
    return set(edges.values())
class Tests(unittest.TestCase):
    def test_long_tapered_horse_face(self):
        ratio=(HEAD[-1][0]-HEAD[0][0])/(max(p[2] for p in HEAD)*2)
        # Shetland head must be long enough to read as equine, not an overlong aardvark snout.
        self.assertGreater(ratio,1.5)
        self.assertLess(ratio,1.85)
        self.assertLess(HEAD[-1][1],HEAD[0][1]-.3)
        self.assertGreater(HEAD[-1][2],HEAD[-2][2])
    def test_sloping_neck(self):
        self.assertGreater(NECK[-1][1]-NECK[0][1],.29)
    def test_manifold_sweeps(self):
        for profile in (HEAD,NECK):
            verts,faces=sweep(profile)
            self.assertEqual(manifold(faces),{2})
            self.assertEqual(len(verts),((len(profile)-1)*4+1)*24+2)
    def test_no_leg_cuffs(self):
        for prefix in ("front","hind"):
            for side in ("L","R"):
                v,f,w=leg(prefix,side)
                self.assertEqual(manifold(f),{2})
                self.assertEqual(len(v),len(w))
                self.assertTrue(all(abs(sum(t)-1)<1e-9 for t in w))
    def test_bad_input(self):
        with self.assertRaises(ValueError):leg("pig","L")
        with self.assertRaises(ValueError):sweep(HEAD,steps=0)
if __name__=="__main__":unittest.main()
