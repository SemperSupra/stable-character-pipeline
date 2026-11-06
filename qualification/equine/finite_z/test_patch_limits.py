import tempfile, unittest
from pathlib import Path
from patch_limits import patch,MIN_LINE,MAX_LINE
FIXTURE='''prefix,side=foot.split("_")
for bone,label in zip(chain,labels):
    bone.use_ik_limit_x=True
    bone.ik_min_x=1
    bone.use_ik_limit_y=True
    bone.ik_max_y=2
    bone.use_ik_limit_z=True
    bone.ik_min_z=math.radians(lim["z"][0])
    bone.ik_max_z=math.radians(lim["z"][1])
'''
class FiniteZ(unittest.TestCase):
    def test_two_exact_limits_and_reversal(self):
        for degrees in (18,24):
            with self.subTest(degrees=degrees),tempfile.TemporaryDirectory() as d:
                a=Path(d)/'original';b=Path(d)/'candidate'
                a.write_text(FIXTURE)
                r=patch(a,b,degrees)
                self.assertEqual(a.read_text(),FIXTURE)
                self.assertEqual(r['front_z_limit_degrees'],degrees)
                self.assertTrue(r['hind_ik_constraints_untouched'])
                self.assertFalse(r['production_eligible'])
                t=b.read_text()
                self.assertEqual(t.count('prefix=="front"'),2)
                self.assertIn('bone.use_ik_limit_x=True',t)
                self.assertIn('bone.use_ik_limit_y=True',t)
                self.assertIn('bone.use_ik_limit_z=True',t)
                self.assertEqual(t.replace(f'-{degrees} if prefix=="front" else lim["z"][0]','lim["z"][0]').replace(f'{degrees} if prefix=="front" else lim["z"][1]','lim["z"][1]'),FIXTURE)
    def test_bounded_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';b=Path(d)/'b';a.write_text(FIXTURE)
            for val in (-18,0,12,30,90):
                with self.assertRaises(ValueError):patch(a,b,val)
    def test_source_and_output_leases(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';b=Path(d)/'b';a.write_text(FIXTURE)
            with self.assertRaises(ValueError):patch(a,a,18)
            b.write_text('occupied')
            with self.assertRaises(ValueError):patch(a,b,18)
    def test_source_drift_and_repeated_assignments(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';b=Path(d)/'b'
            for original in (FIXTURE+MIN_LINE+'\n',FIXTURE+MAX_LINE+'\n', FIXTURE.replace(MIN_LINE,''),FIXTURE.replace('for bone,label in zip(chain,labels):','for bone in chain:'),FIXTURE.replace('prefix,side=foot.split("_")','prefix="hind"')):
                a.write_text(original)
                with self.assertRaises(ValueError):patch(a,b,24)
    def test_refuse_double_patch(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';b=Path(d)/'b';c=Path(d)/'c';a.write_text(FIXTURE)
            patch(a,b,18)
            with self.assertRaises(ValueError):patch(b,c,24)
if __name__=='__main__':unittest.main()
