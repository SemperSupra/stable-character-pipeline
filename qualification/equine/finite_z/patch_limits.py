"""Disposable original synthetic 30-joint *front-only* finite Z IK limit trial.

This changes exactly two assignments within the frozen original source. It is
neither a veterinary ROM limit nor an authorization to modify an owner model.
"""
from pathlib import Path
import argparse, hashlib, json

ALLOWED_DEGREES = (18, 24)
MIN_LINE = 'bone.ik_min_z=math.radians(lim["z"][0])'
MAX_LINE = 'bone.ik_max_z=math.radians(lim["z"][1])'

def patch(source: Path, candidate: Path, degrees: int):
    if degrees not in ALLOWED_DEGREES:
        raise ValueError('finite Z candidate must be approved 18 or 24 degrees')
    if source.resolve() == candidate.resolve() or candidate.exists():
        raise ValueError('refuse source mutation or candidate overwrite')
    original = source.read_bytes()
    text = original.decode('utf-8')
    if text.count(MIN_LINE) != 1 or text.count(MAX_LINE) != 1:
        raise ValueError('exact frozen IK source assignments not found uniquely')
    if text.count('for bone,label in zip(chain,labels):') != 1 or text.count('prefix,side=foot.split("_")') != 1:
        raise ValueError('unknown joint-loop context; do not guess')
    replacements = {
        MIN_LINE: f'bone.ik_min_z=math.radians(-{degrees} if prefix=="front" else lim["z"][0])',
        MAX_LINE: f'bone.ik_max_z=math.radians({degrees} if prefix=="front" else lim["z"][1])',
    }
    updated = text
    for before, after in replacements.items():
        if after in updated:
            raise ValueError('candidate already patched')
        updated = updated.replace(before, after)
    restored = updated
    for before, after in replacements.items():
        if restored.count(after) != 1:
            raise ValueError('replacement ambiguity')
        restored = restored.replace(after, before)
    if restored != text:
        raise ValueError('patch not exactly reversible')
    candidate.parent.mkdir(parents=True,exist_ok=True)
    candidate.write_text(updated)
    return {
        'schema': 'equine.ik.front-z-finite-source-hypothesis.v1',
        'front_z_limit_degrees': degrees,
        'hind_ik_constraints_untouched': True,
        'x_and_y_limits_untouched': True,
        'two_exact_assignments_only': True,
        'source_sha256': hashlib.sha256(original).hexdigest(),
        'candidate_sha256': hashlib.sha256(updated.encode()).hexdigest(),
        'source_owner_modified': False,
        'veterinary_rom_accepted': False,
        'production_eligible': False,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--candidate',type=Path,required=True)
    ap.add_argument('--degrees',type=int,choices=ALLOWED_DEGREES,required=True)
    ap.add_argument('--receipt',type=Path,required=True)
    a=ap.parse_args()
    result=patch(a.source,a.candidate,a.degrees)
    a.receipt.parent.mkdir(parents=True,exist_ok=True)
    a.receipt.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print('FINITE_FRONT_Z_CANDIDATE_NONRELEASE',a.degrees,result['candidate_sha256'])
if __name__=='__main__':main()
