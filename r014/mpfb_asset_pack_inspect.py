"""R014 external system-asset pack provenance and content inventory.
No extracted images, no third party community proxies, no model promotion.
"""
import argparse,hashlib,json,zipfile
from collections import Counter
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("archive",type=Path)
p.add_argument("--out",type=Path,required=True)
args=p.parse_args()
args.out.mkdir(parents=True,exist_ok=True)
hasher=hashlib.sha256()
with args.archive.open("rb") as f:
    while data:=f.read(1024*1024):hasher.update(data)
with zipfile.ZipFile(args.archive) as z:
    assert z.testzip() is None,"archive CRC corruption"
    info=[i for i in z.infolist() if not i.is_dir()]
    assert info and len(info)<10000,"unexpected asset file count"
    assert sum(i.file_size for i in info)<4_000_000_000,"unexpected uncompressed size"
    assert all(i.file_size<250_000_000 for i in info),"unexpected individual file size"
    assert all(not i.filename.startswith("/") and ".." not in i.filename.split("/") for i in info),"unsafe archive paths"
    categories=["eyes","teeth","tongue","eyebrows","eyelashes","hair","skins"]
    counts={c:sum("/"+c+"/" in "/"+i.filename.lower() for i in info) for c in categories}
    assert all(v>0 for v in counts.values()),"incomplete advertised system pack: "+str(counts)
    counttypes=Counter(Path(i.filename).suffix.lower() for i in info)
    assert counttypes[".mhclo"]>0 and counttypes[".mhmat"]>0,"cannot find MakeHuman material/body assets"
    assets=[{"path":i.filename,"bytes":i.file_size} for i in info]
    out={"status":"PASS_SOURCE_ARCHIVE_INTEGRITY_CONTENTS_ONLY",
         "source_url":"https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip",
         "publisher_declared_license":"CC0 (asset-pack catalog; per-item review remains required)",
         "sha256":hasher.hexdigest(),"archive_bytes":args.archive.stat().st_size,
         "files":len(info),"asset_category_counts":counts,"extension_counts":dict(counttypes),
         "asset_manifest":assets,
         "limits":["No native Blender install and skin/eyes/hair review",
                   "No medical/photoreal quality or third-party anatomy rights admission",
                   "Digest first observed in this batch, must PIN on subsequent batches"]}
    (args.out/"system_assets_provenance.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("R014_SYSTEM_ASSETS",json.dumps({k:v for k,v in out.items() if k not in ("asset_manifest","extension_counts")},sort_keys=True))
