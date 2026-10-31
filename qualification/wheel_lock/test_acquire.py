import importlib.util,json,sys,tempfile
from pathlib import Path
import unittest
src=Path(__file__).with_name("acquire.py")
spec=importlib.util.spec_from_file_location("wheels",src)
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
FIXTURE="\n".join([
 "bpy==4.5.0","numpy==1.26.4","packaging==26.3","Cython==3.3.0",
 "certifi==2026.10.23","charset-normalizer==3.5.2",
 "idna==3.20","requests==2.34.2","urllib3==2.8.0","zstandard==0.25.0"])+"\n"
FAKE="""import sys,pathlib
a=sys.argv;dest=pathlib.Path(a[a.index("--dest")+1]);name,version=a[-1].split("==")
if "forcefail" in name:sys.exit(1)
(dest/(name.replace("-","_")+"-"+version+"-py3-none-any.whl")).write_bytes((name+version).encode()*30)
"""
class WheelTests(unittest.TestCase):
 def prepare(self):
  temp=tempfile.TemporaryDirectory()
  root=Path(temp.name)
  script=root/"fake-pip.py";script.write_text(FAKE)
  return temp,root,[sys.executable,str(script)]
 def test_exact_candidate_hashes_and_first_byte_copy(self):
  temp,p,command=self.prepare()
  with temp:
   r=w.collect(FIXTURE,p/"candidate",command)
   self.assertEqual(r["package_count"],10)
   self.assertEqual(len({x["sha256"] for x in r["packages"]}),10)
   self.assertEqual(r["release"],"HELD_R009_NOT_ADMITTED")
   self.assertEqual(r["wheel_license_and_vulnerability_review"],"UNKNOWN")
   self.assertEqual(len((p/"candidate/requirements-hashed.txt").read_text().splitlines()),10)
   self.assertEqual(len(list((p/"candidate/wheelhouse").glob("*.whl"))),10)
 def test_reexecution_does_not_overwrite_original_download(self):
  temp,p,command=self.prepare()
  with temp:
   w.collect(FIXTURE,p/"candidate",command)
   with self.assertRaisesRegex(ValueError,"PREEXISTING_UNVERIFIED_DOWNLOAD_DIR"):
    w.collect(FIXTURE,p/"candidate",command)
 def test_nonbinary_direct_url_denied_before_network(self):
  temp,p,command=self.prepare()
  with temp:
   with self.assertRaisesRegex(ValueError,"NONPINNED_PYTHON_REQUIREMENT"):
    w.collect(FIXTURE+"foo @ https://example.invalid/thing\n",p/"candidate",command)
 def test_core_version_drift_denied_before_network(self):
  temp,p,command=self.prepare()
  with temp:
   with self.assertRaisesRegex(ValueError,"CORE_BLENDER_DEPENDENCY_DRIFT"):
    w.collect(FIXTURE.replace("bpy==4.5.0","bpy==4.5.1"),p/"candidate",command)
 def test_duplicate_normalized_package_denied(self):
  temp,p,command=self.prepare()
  with temp:
   with self.assertRaisesRegex(ValueError,"DUPLICATE_PYTHON_PACKAGE"):
    w.collect(FIXTURE+"charset_normalizer==3.5.2\n",p/"candidate",command)
if __name__=="__main__":unittest.main()
