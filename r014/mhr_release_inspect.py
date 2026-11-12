"""Inspect pinned official MHR asset archive without extracting model weights."""
import argparse,hashlib,json,zipfile
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('archive',type=Path)
p.add_argument('--expected',required=True)
p.add_argument('--out',required=True,type=Path)
a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
h=hashlib.sha256()
with a.archive.open('rb') as f:
    while c:=f.read(1024*1024):h.update(c)
digest=h.hexdigest()
assert digest==a.expected.lower(),'pinned model archive hash mismatch'
with zipfile.ZipFile(a.archive) as z:
    bad=z.testzip()
    assert bad is None,'corrupted archive entry '+str(bad)
    names=z.namelist()
    assert all(not n.startswith('/') and '..' not in n.split('/') for n in names),'archive traversal path'
    licenses=[n for n in names if n.lower().rsplit('/',1)[-1] in ('license','license.txt','license.md')]
    assert licenses,'no bundled model-license file; do not admit rights'
    assets=[{'name':e.filename,'bytes':e.file_size} for e in z.infolist() if not e.is_dir()]
    for i,n in enumerate(licenses):
        data=z.read(n)
        assert len(data)<128*1024,'unexpectedly huge license'
        (a.out/('LICENSE_'+str(i)+'.txt')).write_bytes(data)
receipt={'status':'PASS_ARCHIVE_INTEGRITY_LICENSE_PRESENT_UNADJUDICATED',
         'origin':'facebookresearch/MHR official GitHub release v1.0.1',
         'sha256':digest,'archive_size':a.archive.stat().st_size,
         'license_paths':licenses,'asset_entries':assets,
         'no_model_weights_exported':True,
         'limits':['License text must be independently interpreted',
                   'Not proof model weight train-data rights',
                   'Not an inference or anatomical/video qualification']}
(a.out/'manifest.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print('R014_MHR_ASSET_RECEIPT',json.dumps({'status':receipt['status'],
       'sha256':digest,'license_paths':licenses,'files':len(assets)}))
