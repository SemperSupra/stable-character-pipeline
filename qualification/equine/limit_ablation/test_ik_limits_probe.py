import unittest,tempfile
from pathlib import Path
from ik_limits_probe import ablate,FLAGS

SOURCE='\n'.join('bone.use_ik_limit_'+x+'=True' for x in FLAGS)+'\nunrelated=False\n'
class Tests(unittest.TestCase):
 def test_exact_operation_and_reverse(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'a';b=Path(d)/'b';a.write_text(SOURCE)
   r=ablate(a,b)
   self.assertEqual(b.read_text().replace('bone.use_ik_limit_x=False','bone.use_ik_limit_x=True').replace('bone.use_ik_limit_y=False','bone.use_ik_limit_y=True').replace('bone.use_ik_limit_z=False','bone.use_ik_limit_z=True'),a.read_text())
   self.assertFalse(r['candidate_production_eligible'])
   self.assertFalse(r['owner_source_modified'])
   with self.assertRaises(ValueError):ablate(a,b)
 def test_wrong_source_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'a';b=Path(d)/'b'
   for data in ('',SOURCE+SOURCE,SOURCE.replace('use_ik_limit_y=True','use_ik_limit_y=False')):
    a.write_text(data)
    with self.assertRaises(ValueError):ablate(a,b)
 def test_refuse_inplace(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'a';a.write_text(SOURCE)
   with self.assertRaises(ValueError):ablate(a,a)
if __name__=='__main__':unittest.main()
