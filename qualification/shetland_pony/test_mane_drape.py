import random,unittest
from mane_drape import guides,validate_guides
class Guides(unittest.TestCase):
 def test_seeded_gravity_and_density(self):
    a=guides(random.Random(20261106))
    b=guides(random.Random(20261106))
    self.assertEqual(a,b)
    d=validate_guides(a)
    self.assertEqual(d["guide_count"],1050)
    self.assertTrue(d["all_guides_downward"])
    self.assertTrue(all(v[1][2]<0 for v in a))
 def test_symmetry_and_downward_hair(self):
    d=guides(random.Random(20))
    self.assertEqual(sum(x[1][1]<0 for x in d[:440]),220)
    self.assertEqual(sum(x[1][1]>0 for x in d[:440]),220)
    self.assertEqual(sum(x[4].startswith("tail_") for x in d),380)
 def test_bad_guide(self):
    x=guides(random.Random(2))
    v=list(x[0]);v[1]=(0,0,1);x[0]=tuple(v)
    with self.assertRaises(ValueError):validate_guides(x)
if __name__=="__main__":unittest.main()
