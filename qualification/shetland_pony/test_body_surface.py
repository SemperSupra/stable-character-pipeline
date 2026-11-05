import collections, math, unittest
from body_surface import STATIONS,station_at,pinto_patch,geometry

class TestContinuousBody(unittest.TestCase):
    def test_single_manifold_shell(self):
        p,fs,mask=geometry()
        edges=collections.Counter()
        for face in fs:
            self.assertEqual(len(set(face)),3)
            for a,b in ((face[0],face[1]),(face[1],face[2]),(face[2],face[0])):
                edges[tuple(sorted((a,b)))] += 1
        self.assertEqual(set(edges.values()),{2})
        self.assertEqual(len(p),61*32+2)
        self.assertEqual(len(fs),2*61*32)
    def test_profile_stays_bounded(self):
        for i in range(301):
            x=STATIONS[0][0]+(STATIONS[-1][0]-STATIONS[0][0])*i/300
            z,y,h=station_at(x)
            self.assertTrue(.70<z<1.05)
            self.assertTrue(.04<y<.40 and .075<h<.43)
    def test_pinto_is_material_not_extra_volume(self):
        p,faces,none=geometry(pinto=False)
        a,b,patch=geometry(pinto=True)
        self.assertEqual(p,a)
        self.assertEqual(faces,b)
        self.assertTrue(all(x==0 for x in none))
        self.assertGreater(sum(patch),50)
        self.assertLess(sum(patch),len(patch)*.6)
    def test_no_discontinuity_topological(self):
        p,_,_=geometry()
        for i in range(60):
            for j in range(32):
                a=p[i*32+j];b=p[(i+1)*32+j]
                self.assertLess(math.dist(a,b),.12)
    def test_bad_resolution(self):
        with self.assertRaises(ValueError):geometry(rings=2)
        with self.assertRaises(ValueError):geometry(sides=500)
if __name__=="__main__":unittest.main()
