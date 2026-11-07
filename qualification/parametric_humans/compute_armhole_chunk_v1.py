#!/usr/bin/env python3
"""One bounded eight-sample VTK actor/garment collision job, no source mutation."""
import argparse,hashlib,json
from pathlib import Path
from triangle_surface_bvh_v1 import inspect
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--index',type=int,required=True);p.add_argument('--outdir',type=Path,required=True)
a=p.parse_args()
if a.index<0 or a.index>8:raise ValueError('BAD_INDEX')
frames=(['rest',*range(8)] if a.index==0 else list(range(a.index*8,(a.index+1)*8)))
if not a.outdir.is_dir():raise ValueError('MISSING_DIR')
out=a.outdir / f'bvh_part_{a.index:02d}.json'
if out.exists():raise ValueError('NO_OVERWRITE')
data=a.input.read_bytes();sha=hashlib.sha256(data).hexdigest();r=inspect(data,sha,frames=frames)
if r['frames']!=frames:raise ValueError('FRAME_MISMATCH')
out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
print(json.dumps({'part':a.index,'frames':frames,'sha256':sha,'file':str(out),'total_pairs':{actor:{slot:sum(x['triangle_contact_pairs'] for x in rows) for slot,rows in v['slots'].items()} for actor,v in r['actors'].items()}},sort_keys=True))
