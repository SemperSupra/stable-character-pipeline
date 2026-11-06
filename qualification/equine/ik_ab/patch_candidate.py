"""Source-exact synthetic pony A/B hypothesis, applied only to disposable checkout.

This is an experimental carpus REST offset, not anatomical acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path

ORIGINAL = 'carpus=(x-.006,y,.432)'
PATCHED = 'carpus=(x-.046,y,.432)'

def patch(source: Path, target: Path) -> dict:
    if source.resolve() == target.resolve():
        raise ValueError('refuse in-place modification of source')
    raw=source.read_bytes()
    text=raw.decode('utf-8')
    if text.count(ORIGINAL)!=1 or PATCHED in text:
        raise ValueError('source not exactly the expected unpatched anatomy')
    updated=text.replace(ORIGINAL,PATCHED)
    if updated.replace(PATCHED, ORIGINAL)!=text:
        raise ValueError('non-reversible patch')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        raise ValueError('refuse overwrite of existing candidate')
    target.write_text(updated)
    return {'schema':'equine.experimental.carpus-source-patch.v1',
            'shift_posterior_m':0.04,'source_name':'equine_anatomy.py',
            'before_sha256':hashlib.sha256(raw).hexdigest(),
            'after_sha256':hashlib.sha256(updated.encode()).hexdigest(),
            'exactly_one_replacement':True,'owner_source_modified':False,
            'animal_anatomy_accepted':False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--candidate',required=True,type=Path)
    ap.add_argument('--receipt',required=True,type=Path)
    a=ap.parse_args()
    receipt=patch(a.source,a.candidate)
    a.receipt.parent.mkdir(parents=True,exist_ok=True)
    a.receipt.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('SOURCE_EXACT_REVERSIBLE_CARPUS_HYPOTHESIS',receipt['after_sha256'])
if __name__=='__main__':main()
