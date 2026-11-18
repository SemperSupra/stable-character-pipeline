import io,stat,unittest,zipfile
from audit import CATALOG,validate_zip
def fixture(entries):
 b=io.BytesIO()
 with zipfile.ZipFile(b,"w") as z:
  for n,v in entries:z.writestr(n,v)
 return b.getvalue()
class Audit(unittest.TestCase):
 def test_catalog_packs(self):
  self.assertEqual(set(CATALOG),{"shirts01","pants01","shoes01"})
  self.assertTrue(all(p["license"]=="CC0" for p in CATALOG.values()))
 def test_expected_outfit_candidate(self):
  m=validate_zip(fixture([("clothes/skalldyrssuppe_tube_top_funky_colors/shirt.mhclo","test")]),"shirts01")
  self.assertTrue(m["selected_asset_present"]["skalldyrssuppe_tube_top_funky_colors"])
  self.assertFalse(m["per_file_license_admitted"])
 def test_zip_slip_rejected(self):
  with self.assertRaisesRegex(ValueError,"ZIP_UNSAFE_PATH"):validate_zip(fixture([("../forged.mhclo","x")]),"shirts01")
 def test_absolute_rejected(self):
  with self.assertRaisesRegex(ValueError,"ZIP_UNSAFE_PATH"):validate_zip(fixture([("/passwd","x")]),"pants01")
 def test_backslash_rejected(self):
  with self.assertRaisesRegex(ValueError,"ZIP_UNSAFE_PATH"):validate_zip(fixture([("nested\\file","x")]),"pants01")
 def test_duplicate_rejected(self):
  with self.assertRaisesRegex(ValueError,"ZIP_DUPLICATE_ENTRY"):validate_zip(fixture([("same.mhclo","a"),("same.mhclo","b")]),"shoes01")
 def test_non_archive_rejected(self):
  with self.assertRaises(zipfile.BadZipFile):validate_zip(b"not a ZIP","pants01")
 def test_no_mesh_is_hold(self):
  m=validate_zip(fixture([("README.txt","test")]),"shirts01")
  self.assertEqual(m["mhclo_count"],0)
  self.assertFalse(m["per_file_license_admitted"])
 def test_catalog_cc0_conflict_is_typed_hold(self):
  data=fixture([("clothes/skalldyrssuppe_tube_top_funky_colors/shirt.mhclo","# license AGPL3")])
  result=validate_zip(data,"shirts01")
  self.assertTrue(result["license_conflict_hold"])
  self.assertEqual(result["admission"],"HOLD_CATALOG_VS_EMBEDDED_LICENSE")
  self.assertEqual(result["catalog_vs_embedded_license_conflicts"],["shirt"])
 def test_explicit_cc0_header_does_not_imply_all_asset_rights(self):
  data=fixture([("clothes/toigo_camisole_top/cami.mhclo","# license CC0")])
  result=validate_zip(data,"shirts01")
  self.assertFalse(result["license_conflict_hold"])
  self.assertFalse(result["per_file_license_admitted"])
 def test_symlink_rejected(self):
  i=zipfile.ZipInfo("fake.mhclo");i.create_system=3;i.external_attr=(stat.S_IFLNK|0o777)<<16
  b=io.BytesIO()
  with zipfile.ZipFile(b,"w") as z:z.writestr(i,"elsewhere")
  with self.assertRaisesRegex(ValueError,"ZIP_SYMLINK"):validate_zip(b.getvalue(),"shoes01")
if __name__=="__main__":unittest.main()
