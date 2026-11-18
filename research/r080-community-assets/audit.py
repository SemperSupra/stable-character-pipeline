"""Official MakeHuman community CC0 archive census; no extraction or asset upload."""
import argparse,hashlib,io,json,pathlib,stat,sys,urllib.parse,urllib.request,zipfile
CATALOG={
 "shirts01":{"url":"https://files.makehumancommunity.org/asset_packs/shirts01/shirts01_cc0.zip","catalog":"https://static.makehumancommunity.org/assets/assetpacks/shirts01.html","license":"CC0","candidates":["skalldyrssuppe_tube_top_funky_colors","toigo_camisole_top"],"max_bytes":40000000},
 "pants01":{"url":"https://files.makehumancommunity.org/asset_packs/pants01/pants01_cc0.zip","catalog":"https://static.makehumancommunity.org/assets/assetpacks/pants01.html","license":"CC0","candidates":["cortu_jeans_shorts","cortu_cargo_pants"],"max_bytes":35000000},
 "shoes01":{"url":"https://files.makehumancommunity.org/asset_packs/shoes01/shoes01_cc0.zip","catalog":"https://static.makehumancommunity.org/assets/assetpacks/shoes01.html","license":"CC0","candidates":["scailman_gogo_platform_boots","toigo_ankle_boots_female"],"max_bytes":100000000}
}
def validate_zip(data,pack):
 if len(data)>CATALOG[pack]["max_bytes"]:raise ValueError("ZIP_COMPRESSED_LIMIT")
 items=[];names=set();total=0
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  for i in z.infolist():
   path=pathlib.PurePosixPath(i.filename)
   if i.filename.startswith(("/","\\")) or "\\" in i.filename or ".." in path.parts or ":" in i.filename:raise ValueError("ZIP_UNSAFE_PATH")
   if str(path) in names:raise ValueError("ZIP_DUPLICATE_ENTRY")
   names.add(str(path))
   if stat.S_IFMT(i.external_attr>>16)==stat.S_IFLNK:raise ValueError("ZIP_SYMLINK")
   total+=i.file_size
   if len(names)>10000 or total>550000000:raise ValueError("ZIP_RESOURCE_LIMIT")
   if not i.is_dir():items.append(i)
  if z.testzip() is not None:raise ValueError("ZIP_CRC_FAILURE")
  assets=sorted(i.filename for i in items if i.filename.lower().endswith(".mhclo"))
  # Inspect exactly the proposed wardrobe .mhclo metadata only; not geometry or textures.
  license_headers={}
  conflicts=[]
  for n in assets:
   stem=pathlib.PurePosixPath(n).stem
   lines=z.read(n).decode("utf8","replace").splitlines()[:80]
   headers=[line.strip()[:180] for line in lines if "license" in line.lower()][:4]
   license_headers[stem]=headers
   if any("AGPL" in line.upper() or "GPL" in line.upper() for line in headers):
    conflicts.append(stem)
  return {"candidate_license_headers":license_headers,
          "catalog_vs_embedded_license_conflicts":sorted(conflicts),
          "license_conflict_hold":bool(conflicts),
          "admission":"HOLD_CATALOG_VS_EMBEDDED_LICENSE" if conflicts else "HOLD_PER_FILE_LICENSE_VALIDATION",
          "file_count":len(items),"expanded_bytes":total,"mhclo_count":len(assets),
          "selected_asset_present":{s:any(s in p.lower() for p in assets) for s in CATALOG[pack]["candidates"]},
          "sample_mhclo_paths":assets[:20],"per_file_license_admitted":False}
def download(pack):
 req=urllib.request.Request(CATALOG[pack]["url"],headers={"User-Agent":"StableCharacter-AssetAudit/1.0"})
 with urllib.request.urlopen(req,timeout=65) as response:
  url=urllib.parse.urlsplit(response.geturl())
  if url.scheme!="https" or url.hostname not in ("files.makehumancommunity.org","files2.makehumancommunity.org"):raise ValueError("UNAPPROVED_REDIRECT")
  m=CATALOG[pack]["max_bytes"];data=response.read(m+1)
  if len(data)>m:raise ValueError("ZIP_COMPRESSED_LIMIT")
  return data
def main():
 p=argparse.ArgumentParser();p.add_argument("--pack",choices=sorted(CATALOG),required=True);p.add_argument("--out",required=True);a=p.parse_args()
 data=download(a.pack);record={"schema":"scp.r080.official-asset-census.v1","pack":a.pack,"archive_url":CATALOG[a.pack]["url"],
   "catalog":CATALOG[a.pack]["catalog"],"catalog_license":"CC0","archive_sha256":hashlib.sha256(data).hexdigest(),
   "archive_bytes":len(data),"asset_derivative_admitted":False,"real_character_accepted":False,
   "admission":"CATALOG_ONLY_HOLD_PER_FILE_REVIEW",**validate_zip(data,a.pack)}
 pathlib.Path(a.out).write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")
 print("R080_OFFICIAL_ARCHIVE_METADATA",json.dumps(record,sort_keys=True),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as exc:
  print("R080_ARCHIVE_RED",type(exc).__name__,str(exc),file=sys.stderr);sys.exit(12)
