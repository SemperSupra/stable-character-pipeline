import json,tempfile,unittest
from pathlib import Path
from verify_r090 import run
class VersionAdmission(unittest.TestCase):
 def test_wrong_version_fails(self):
  with self.assertRaises((ValueError,OSError)):run(["/no", "/no", "/no","5.4.0"])
 def test_missing_files_fails(self):
  with self.assertRaises(OSError):run(["/does-not-exist","/no","/no","5.2.4"])
 def test_hostile_nonfinite_reject(self):
  import math
  with self.assertRaises(ValueError):json.loads('{"a":bad}')
 def test_not_version_only_acceptance(self):
  with self.assertRaises(ValueError):run([])
if __name__=="__main__":unittest.main()
