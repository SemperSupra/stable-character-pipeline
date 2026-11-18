import io,unittest,zipfile,hashlib
import wardrobe_contract as c
class Contract(unittest.TestCase):
 def test_original_fictional_names(self):self.assertTrue(c.test_contract())
 def test_license_exact_cc0(self):
  self.assertTrue(c.license_admitted("# license CC0\n"))
  self.assertTrue(c.license_admitted("# license: CC0\n"))
  self.assertTrue(c.license_admitted("# license CC-0\n"))
 def test_agpl_conflict_rejected(self):
  self.assertFalse(c.license_admitted("# license AGPL3"))
 def test_license_missing_rejected(self):
  self.assertFalse(c.license_admitted("name toigo"))
 def test_conflicting_headers_rejected(self):
  self.assertFalse(c.license_admitted("# license CC0\n# license AGPL3\n"))
 def test_false_source_hash_rejected(self):
  with self.assertRaisesRegex(ValueError,"SOURCE_ARCHIVE_HASH_MISMATCH"):c.source_archive("shirts01",b"forge")
 def test_unknown_pack_rejected(self):
  with self.assertRaisesRegex(ValueError,"UNKNOWN_PACK"):c.source_archive("evil",b"forge")
 def test_missing_mhclo_rejected(self):
  mem=io.BytesIO()
  with zipfile.ZipFile(mem,'w') as z:z.writestr("README","hello")
  with zipfile.ZipFile(io.BytesIO(mem.getvalue())) as z:
   with self.assertRaisesRegex(ValueError,"SELECTED_MHCLO_ABSENT"):c.select_bytes(z,"toigo_camisole_top")
 def test_empty_garment_pair_rejected(self):
  old=c.OUTFITS["JuniperOriginal"]
  try:
   c.OUTFITS["JuniperOriginal"]=()
   with self.assertRaisesRegex(ValueError,"WARDROBE_LAYER_COUNT"):c.test_contract()
  finally:c.OUTFITS["JuniperOriginal"]=old
 def test_color_range_rejected(self):
  old=c.OUTFITS["AsterOriginal"]
  try:
   c.OUTFITS["AsterOriginal"]=tuple((p,n,(9,9,9,1)) for p,n,_ in old)
   with self.assertRaisesRegex(ValueError,"GARMENT_COLOR_INVALID"):c.test_contract()
  finally:c.OUTFITS["AsterOriginal"]=old
if __name__=="__main__":unittest.main()
