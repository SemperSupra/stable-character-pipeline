import unittest,tempfile
from pathlib import Path
from select_axis import alter

ORIGINAL='bone.use_ik_limit_x=True\nbone.use_ik_limit_y=True\nbone.use_ik_limit_z=True\nunrelated=False\n'
class SelectAxis(unittest.TestCase):
 def test_per_axis_exact_and_reversible(self):
  for axis in 'xyz':
   with self.subTest(axis=axis), tempfile.TemporaryDirectory() as d:
    a=Path(d)/'a';b=Path(d)/'b';a.write_text(ORIGINAL)
    result=alter(a,b,axis)
    self.assertEqual(result['changed_ik_axes'],[axis]);self.assertFalse(result['axis_production_eligible'])
    self.assertEqual(b.read_text().replace(f'bone.use_ik_limit_{axis}=False',f'bone.use_ik_limit_{axis}=True'),ORIGINAL)
    self.assertEqual(a.read_text(),ORIGINAL)
 def test_unknown_axis(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'a';b=Path(d)/'b';a.write_text(ORIGINAL)
   for axis in ('all','X','',':'):
    with self.assertRaises(ValueError):alter(a,b,axis)
 def test_bad_source(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'a';b=Path(d)/'b'
   for text in ('',ORIGINAL+ORIGINAL,ORIGINAL.replace('x=True','x=False')):
    a.write_text(text)
    with self.assertRaises(ValueError):alter(a,b,'x')
 def test_source_overwrite_refused(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'a';a.write_text(ORIGINAL)
   with self.assertRaises(ValueError):alter(a,a,'x')

 def test_existing_candidate_is_not_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   original=Path(d)/'source.py';candidate=Path(d)/'already-existing.py'
   original.write_text(ORIGINAL);candidate.write_text('owner-data-unmodified')
   with self.assertRaisesRegex(ValueError,'refuse overwrite'):
    alter(original,candidate,'z')
   self.assertEqual(candidate.read_text(),'owner-data-unmodified')
   self.assertEqual(original.read_text(),ORIGINAL)
if __name__=='__main__':unittest.main()
