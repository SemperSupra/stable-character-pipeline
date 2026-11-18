import io,stat,unittest,zipfile
from system_asset_census import candidate_record,inspect_zip,CATEGORIES
def fixture(extra=()):
 out=io.BytesIO()
 with zipfile.ZipFile(out,"w") as z:
  for c in sorted(CATEGORIES):z.writestr(c+"/README.txt","public test fixture")
  for name,data in extra:z.writestr(name,data)
 return zipfile.ZipFile(io.BytesIO(out.getvalue()))
class SourceOnly(unittest.TestCase):
 def test_explicit_cc0_header_candidate(self):
  x=candidate_record("hair/long01/long01.mhclo",b"# license CC0")
  self.assertTrue(x["header_cc0"]);self.assertFalse(x["catalog_header_conflict"])
 def test_publisher_explicit_cc0_release_sentence(self):
  x=candidate_record("hair/long01/long01.mhclo",b"# This asset was explicitly released as CC0 in september 2020. The license")
  self.assertTrue(x["header_cc0"])
  self.assertFalse(x["catalog_header_conflict"])
 def test_publisher_notice_and_agpl_conflict_is_held(self):
  x=candidate_record("hair/long01/long01.mhclo",b"# This asset was explicitly released as CC0 in september 2020. The license\n# license AGPL3")
  self.assertFalse(x["header_cc0"])
 def test_agpl_header_rejected(self):
  x=candidate_record("hair/long01/long01.mhclo",b"# license AGPL3")
  self.assertTrue(x["catalog_header_conflict"]);self.assertFalse(x["header_cc0"])
 def test_both_headers_rejected(self):
  x=candidate_record("hair/long01/long01.mhclo",b"# license CC0\n# license AGPL3")
  self.assertFalse(x["header_cc0"])
 def test_missing_header_held(self):
  self.assertFalse(candidate_record("hair/x.mhclo",b"name sample")["header_cc0"])
 def test_safe_census_does_not_accept_models(self):
  with fixture([("hair/long01/long01.mhclo",b"# license CC0")]) as z:out=inspect_zip(z)
  self.assertFalse(out["per_item_model_derivative_rights_accepted"])
  self.assertTrue(out["candidate_assets"][0]["header_cc0"])
 def test_reject_zip_slip(self):
  with fixture([("../foo","x")]) as z:
   with self.assertRaisesRegex(ValueError,"ZIP_UNSAFE_PATH"):inspect_zip(z)
 def test_reject_absolute(self):
  with fixture([("/var/file","x")]) as z:
   with self.assertRaisesRegex(ValueError,"ZIP_UNSAFE_PATH"):inspect_zip(z)
 def test_reject_duplicate(self):
  with fixture([("hair/repeated.mhclo","a"),("hair/repeated.mhclo","b")]) as z:
   with self.assertRaisesRegex(ValueError,"ZIP_DUPLICATE_PATH"):inspect_zip(z)
 def test_reject_missing_surface_category(self):
  f=io.BytesIO()
  with zipfile.ZipFile(f,"w") as z:z.writestr("hair/long01/long01.mhclo","test")
  with zipfile.ZipFile(io.BytesIO(f.getvalue())) as z:
   with self.assertRaisesRegex(ValueError,"MISSING_SURFACE_ASSET_CATEGORY"):inspect_zip(z)
 def test_reject_symlink(self):
  i=zipfile.ZipInfo("hair/linked.mhclo");i.create_system=3;i.external_attr=(stat.S_IFLNK|0o777)<<16
  f=io.BytesIO()
  with zipfile.ZipFile(f,"w") as z:
   for c in CATEGORIES:z.writestr(c+"/file.txt","safe")
   z.writestr(i,"other")
  with zipfile.ZipFile(io.BytesIO(f.getvalue())) as z:
   with self.assertRaisesRegex(ValueError,"ZIP_SYMLINK"):inspect_zip(z)
if __name__=="__main__":unittest.main()
