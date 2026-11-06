import unittest,math
from curved_groom import curve_card,ROWS,VERTS_PER_CARD

class CurvedGroomTests(unittest.TestCase):
    def setUp(self):
        self.card=[(0.,-.005,1.),(0.,.005,1.),(-.21,-.001,.82),(-.21,.001,.82)]
    def test_root_preserved_and_curved_four_segments(self):
        vv,ff=curve_card(self.card,11,"neck")
        self.assertEqual(len(vv),VERTS_PER_CARD)
        self.assertEqual(len(ff),8)
        self.assertEqual(vv[0],self.card[0])
        self.assertEqual(vv[1],self.card[1])
        self.assertLess(vv[-2][2],self.card[2][2]-.07)
        self.assertLess(vv[4][2],(.5*self.card[0][2]+.5*self.card[2][2])-.02)
        self.assertTrue(all(len(set(f))==3 for f in ff))
        self.assertEqual((vv,ff),curve_card(self.card,11,"neck"))
    def test_region_differences(self):
        mane,_=curve_card(self.card,2,"neck")
        tail,_=curve_card(self.card,2,"tail_1")
        self.assertLess(mane[-1][2],tail[-1][2])
        for bone in ("head","tail_1","tail_2","tail_3"):
            self.assertEqual(len(curve_card(self.card,2,bone)[0]),ROWS*2)
    def test_hostile_inputs(self):
        with self.assertRaises(ValueError):curve_card(self.card,1,"bad")
        with self.assertRaises(ValueError):curve_card(self.card,1.2,"neck")
        with self.assertRaises(ValueError):curve_card(self.card[:-1],0,"neck")
        bad=list(self.card);bad[0]=(math.nan,0,0)
        with self.assertRaises(ValueError):curve_card(bad,0,"neck")

if __name__=="__main__":unittest.main()
