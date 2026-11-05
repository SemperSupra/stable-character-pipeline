import math,unittest
from equine_anatomy import chain,JOINTS,LIMITS,TWIST_MAX_DEG,validate_structure
class Anatomy(unittest.TestCase):
 def specs(self):
    roots=[("root",None,(-.09,0,.73),(-.09,0,.84)),
    ("body","root",(-.4,0,.8),(.38,0,.8)),
    ("neck","body",(.34,0,.83),(.65,0,1.13)),
    ("head","neck",(.65,0,1.13),(.96,0,.87)),
    ("jaw","head",(.82,0,.91),(.97,0,.82)),
    ("ear_L","head",(.73,-.13,1.20),(.75,-.14,1.37)),
    ("ear_R","head",(.73,.13,1.20),(.75,.14,1.37)),
    ("tail_1","body",(-.57,0,.88),(-.73,0,.76)),
    ("tail_2","tail_1",(-.73,0,.76),(-.85,0,.55)),
    ("tail_3","tail_2",(-.85,0,.55),(-.89,0,.35))]
    for side in ("L","R"):
        for prefix,x in (("front",.4),("hind",-.48)):
            roots.extend(chain(prefix,side,x,-.2 if side=="L" else .2,
                              .81 if prefix=="front" else .78))
    return roots
 def test_30_bone_anatomy(self):
    self.assertTrue(validate_structure(self.specs()))
    self.assertEqual(len(self.specs()),30)
 def test_separate_stifle_and_hock(self):
    bones={x[0]:x for x in self.specs()}
    for side in ("L","R"):
      st=bones["hind_"+side+"_stifle"]
      lo=bones["hind_"+side+"_lower"]
      self.assertEqual(st[3],lo[2])
      self.assertNotEqual(st[2],st[3])
      self.assertGreater(st[2][0],st[3][0]) # stifle rostral to hock
 def test_sagittal_limits(self):
    for name,axes in LIMITS.items():
      self.assertLess(axes["x"][0],0)
      self.assertGreater(axes["x"][1],0)
      self.assertLessEqual(axes["x"][1]-axes["x"][0],210)
      self.assertLessEqual(axes["z"][1],15)
    self.assertLessEqual(TWIST_MAX_DEG,10)
 def test_missing_stifle(self):
    s=[v for v in self.specs() if v[0]!="hind_L_stifle"]
    with self.assertRaises(ValueError):validate_structure(s)
 def test_zero_length(self):
    s=self.specs()
    s[-1]=(s[-1][0],s[-1][1],s[-1][2],s[-1][2])
    with self.assertRaises(ValueError):validate_structure(s)
if __name__=="__main__":unittest.main()
