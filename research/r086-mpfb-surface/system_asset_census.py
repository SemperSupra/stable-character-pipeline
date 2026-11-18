"""R086 official MakeHuman CC0 system-pack surface candidate census.
Read-only source metadata, no extracted image, mesh or texture publication.
"""
import argparse,hashlib,io,json,pathlib,re,stat,sys,urllib.parse,urllib.request,zipfile
URI="https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip"
EXPECTED_SHA="b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107"
MAX_ARCHIVE=420_000_000
MAX_EXPANDED=2_000_000_000
CATEGORIES={"hair","eyes","eyebrows","eyelashes","skins","teeth","tongue"}
CANDIDATES={
 "hair/long01/long01.mhclo",
 "hair/short01/short01.mhclo",
 "eyes/high-poly/high-poly.mhclo",
 "eyebrows/eyebrow001/eyebrow001.mhclo",
 "eyelashes/eyelashes01/eyelashes01.mhclo",
 "skins/young_caucasian_female/young_caucasian_female.mhmat",
 "skins/young_caucasian_male/young_caucasian_male.mhmat"
}
def fail(cond,code):
 if not cond:raise ValueError(code)
def candidate_record(path,blob):
 lines=blob.decode("utf8","replace").splitlines()[:100]
 headers=[l.strip()[:180] for l in lines if "license" in l.lower()][:8]
 states=[l.lower().replace(":"," ").strip() for l in headers]
 explicit=any(re.match(r"^#?\s*license\s+cc[- ]?0(?:\s|$)",s) or re.match(r"^#?\s*this asset was explicitly released as cc[- ]?0\b",s) for s in states)
 conflict=any("agpl" in s or re.search(r"\bgpl\d",s) for s in states)
 return {"path":path,"sha256":hashlib.sha256(blob).hexdigest(),
         "license_headers":headers,"header_cc0":explicit and not conflict,
         "catalog_header_conflict":conflict,
         "status":"HEADER_CC0_CANDIDATE_NOT_MODEL_APPROVED" if explicit and not conflict else "HOLD_ITEM_LICENSE_OR_MISSING"}
def inspect_zip(z):
 total=0;seen=set();categories={k:0 for k in CATEGORIES};inventory=[]
 for info in z.infolist():
  path=pathlib.PurePosixPath(info.filename)
  fail(info.filename!="" and not info.filename.startswith(("/","\\")) and "\\" not in info.filename and ".." not in path.parts and ":" not in info.filename,"ZIP_UNSAFE_PATH")
  fail(info.filename not in seen,"ZIP_DUPLICATE_PATH")
  seen.add(info.filename)
  fail(stat.S_IFMT(info.external_attr>>16)!=stat.S_IFLNK,"ZIP_SYMLINK")
  total+=info.file_size
  fail(len(seen)<15000 and info.file_size<220_000_000 and total<MAX_EXPANDED,"ZIP_EXPANDED_LIMIT")
  if info.is_dir():continue
  parts=[p.lower() for p in path.parts]
  for c in CATEGORIES:
   if c in parts:categories[c]+=1
  if info.filename.lower().endswith((".mhclo",".mhmat")):
   # Require small control metadata only. Never scan/publish source PNG or mesh content.
   fail(info.file_size<2_000_000,"METADATA_FILE_OVERSIZED")
   if len(inventory)>=1000:raise ValueError("METADATA_ENTRY_QUOTA")
   inventory.append(candidate_record(info.filename,z.read(info)))
 fail(z.testzip() is None,"ZIP_CRC_RED")
 fail(all(categories.values()),"MISSING_SURFACE_ASSET_CATEGORY")
 selected=[]
 for c in sorted(CANDIDATES):
  matches=[x for x in inventory if x["path"].lower().endswith(c)]
  selected.extend(matches)
 return {"file_count":len(seen),"uncompressed_bytes":total,"categories":categories,
         "control_file_count":len(inventory),
         "candidate_assets":selected,"listed_candidates":sorted(CANDIDATES),
         "license_conflicts":sorted(x["path"] for x in inventory if x["catalog_header_conflict"]),
         "missing_requested":sorted(c for c in CANDIDATES if not any(x["path"].lower().endswith(c) for x in inventory)),
         "per_item_model_derivative_rights_accepted":False}
def retrieve():
 req=urllib.request.Request(URI,headers={"User-Agent":"StableCharacterSystemAssetAudit/1.0"})
 with urllib.request.urlopen(req,timeout=120) as response:
  effective=urllib.parse.urlsplit(response.geturl())
  fail(effective.scheme=="https" and effective.hostname in ("files2.makehumancommunity.org","files.makehumancommunity.org"),"UNAPPROVED_SOURCE_REDIRECT")
  data=response.read(MAX_ARCHIVE+1)
  fail(len(data)<=MAX_ARCHIVE,"SOURCE_ARCHIVE_MAX_BYTES")
  return data
def main():
 p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
 data=retrieve()
 sha=hashlib.sha256(data).hexdigest()
 fail(sha==EXPECTED_SHA,"PINNED_PUBLISHER_ARCHIVE_SHA_RED")
 with zipfile.ZipFile(io.BytesIO(data)) as z:meta=inspect_zip(z)
 result={"schema":"scp.r086.official-system-surface-census.v1","publisher_archive_sha256":sha,
         "source_url":URI,"archive_bytes":len(data),
         "admission":"SOURCE_CENSUS_ONLY_NO_SURFACE_ATTACHMENT",
         "actual_model_surface_accepted":False,"photoreal_accepted":False,
         "real_identity_accepted":False,"released":False,**meta}
 pathlib.Path(a.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print("R086_SURFACE_ARCHIVE",json.dumps(result,sort_keys=True),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as exc:
  print("R086_SURFACE_RED",type(exc).__name__,str(exc),file=sys.stderr);sys.exit(12)
