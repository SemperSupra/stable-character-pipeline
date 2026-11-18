"""R082 exact-source CC0 candidate wardrobe admission for original fictional MPFB humans."""
import hashlib,io,pathlib,re,stat,zipfile
PACKS={
 "shirts01":{"sha256":"a5a723b0e84a109bb190fcfeac7f1de4138d875da3e30fe5b3340eac9f38bcd3","url":"https://files.makehumancommunity.org/asset_packs/shirts01/shirts01_cc0.zip","max_bytes":40000000},
 "pants01":{"sha256":"e4e0ec60db34f279be291a83cfd7b342a7c5cf09bb7676682a5f39f4f6ac4ad9","url":"https://files.makehumancommunity.org/asset_packs/pants01/pants01_cc0.zip","max_bytes":35000000},
 "shoes01":{"sha256":"ded3f70428505eabbf1f6d7b5f61196a7366ef20757103d276ad0ed336c35ada","url":"https://files.makehumancommunity.org/asset_packs/shoes01/shoes01_cc0.zip","max_bytes":100000000}
}
OUTFITS={
 "AsterOriginal":(
  ("shirts01","toigo_bodice-style_top",(0.78,0.73,0.69,1)),
  ("pants01","toigo_harem_pants",(0.13,0.22,0.38,1)),
  ("shoes01","toigo_stiletto_booties",(0.91,0.89,0.86,1))
 ),
 "JuniperOriginal":(
  ("shirts01","toigo_camisole_top",(0.92,0.92,0.91,1)),
  ("pants01","toigo_wool_pants",(0.12,0.21,0.42,1)),
  ("shoes01","toigo_ballet_flats",(0.91,0.91,0.91,1))
 )
}
def require(ok,code):
 if not ok:raise ValueError(code)
def source_archive(pack,data):
 require(pack in PACKS,"UNKNOWN_PACK")
 require(len(data)<=PACKS[pack]["max_bytes"],"ZIP_QUOTA_EXCEEDED")
 require(hashlib.sha256(data).hexdigest()==PACKS[pack]["sha256"],"SOURCE_ARCHIVE_HASH_MISMATCH")
 z=zipfile.ZipFile(io.BytesIO(data));names=set();size=0
 for i in z.infolist():
  path=pathlib.PurePosixPath(i.filename)
  require(i.filename and not i.filename.startswith(("/","\\")) and "\\" not in i.filename and ".." not in path.parts and ":" not in i.filename,"ZIP_PATH_UNSAFE")
  require(str(path) not in names,"ZIP_DUPLICATE_MEMBER")
  names.add(str(path));size+=i.file_size
  require(stat.S_IFMT(i.external_attr>>16)!=stat.S_IFLNK,"ZIP_SYMLINK")
  require(size<=550000000 and len(names)<=10000,"ZIP_UNPACK_QUOTA")
 require(z.testzip() is None,"ZIP_CRC_RED")
 return z
def license_admitted(text):
 headers=[x.strip().lower() for x in text.splitlines()[:80] if "license" in x.lower()]
 # Explicit positive per-file CC0 only; old AGPL3 notices intentionally rejected.
 return any(bool(re.match(r"^#?\s*license\s*:?\s*cc[- ]?0(?:\s|$)",x)) for x in headers) and not any("agpl" in x or "gpl" in x for x in headers)
def select_bytes(z,asset):
 prefix="clothes/"+asset+"/";filename=prefix+asset+".mhclo"
 require(filename in z.namelist(),"SELECTED_MHCLO_ABSENT")
 require(license_admitted(z.read(filename).decode("utf8","replace")),"ASSET_LICENSE_NOT_CC0_ADMITTED")
 members=[n for n in z.namelist() if n.startswith(prefix) and not n.endswith("/")]
 require(len(members)>=2,"ASSET_SIDE_FILES_MISSING")
 return filename,members
def test_contract():
 require(set(OUTFITS)=={"AsterOriginal","JuniperOriginal"},"ACTOR_PAIR_CHANGED")
 for actor,rows in OUTFITS.items():
  require(len(rows)==3,"WARDROBE_LAYER_COUNT")
  require({p for p,_,_ in rows}==set(PACKS),"MISSING_REQUIRED_OUTFIT_LAYERS")
  require(all(len(rgba)==4 and all(type(c) in (float,int) and 0<=c<=1 for c in rgba) for _,_,rgba in rows),"GARMENT_COLOR_INVALID")
 return True
