#!/usr/bin/env python3
"""Independent, bounded 73-pose contact receipt assembly (original synthetic only).

Allows inexpensive VTK 8-pose process isolation without changing the contact
oracle or silently dropping failed samples. This joins evidence; never validates
cloth, biology, or release readiness.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
SCHEMA='scp.r009.makehuman35.triangle_bvh_contact.v1'
ACTORS=('AsterOriginal','JuniperOriginal')
SLOTS=('costume_top','costume_bottom','costume_trim','footwear')
FULL=['rest',*range(72)]
FALSE_KEYS=('vertex_signed_inclusion_qualified','native_blender_evaluated',
 'cloth_physics_qualified','no_triangle_crossing_proven','wearable_fit_accepted',
 'natural_gait_accepted','release_approved')
class BatchError(ValueError):pass

def validate(receipt):
    if type(receipt) is not dict or receipt.get('schema')!=SCHEMA:raise BatchError('BAD_SCHEMA')
    if type(receipt.get('source_sha256')) is not str or len(receipt['source_sha256'])!=64 or any(c not in '0123456789abcdef' for c in receipt['source_sha256']):raise BatchError('INVALID_SOURCE_HASH')
    if any(receipt.get(k) is not False for k in FALSE_KEYS):raise BatchError('FALSE_SCIENCE_APPROVAL')
    fs=receipt.get('frames')
    if type(fs) is not list or not fs or len(fs)>73 or receipt.get('frame_count')!=len(fs):raise BatchError('BAD_FRAMES')
    if any(f not in FULL for f in fs) or len(set(map(str,fs)))!=len(fs) or fs!=sorted(fs,key=lambda f:-1 if f=='rest' else f):raise BatchError('FRAME_ORDER_OR_DUPLICATE')
    if set(receipt.get('actors',{}))!=set(ACTORS):raise BatchError('BAD_ACTORS')
    found_cross=False
    for a in ACTORS:
        rec=receipt['actors'][a]
        if set(rec.get('slots',{}))!=set(SLOTS):raise BatchError('BAD_SLOTS')
        for slot in SLOTS:
            rows=rec['slots'][slot]
            if len(rows)!=len(fs):raise BatchError('SHORT_SLOT')
            for f,row in zip(fs,rows):
                if type(row) is not dict or row.get('frame')!=f:raise BatchError('MISMATCHED_ROW_CLOCK')
                num=row.get('triangle_contact_pairs')
                if type(num) is not int or num<0:raise BatchError('INVALID_PAIR_COUNT')
                for key in ('body_triangle_count','garment_triangle_count'):
                    if type(row.get(key)) is not int or row[key]<=0:raise BatchError('INVALID_FACE_COUNT')
                found_cross|=num>0
        if rec.get('any_crossings') != any(x['triangle_contact_pairs']>0 for rows in rec['slots'].values() for x in rows):raise BatchError('FALSIFIED_ACTOR_CROSSING')
    if receipt.get('any_crossings') != found_cross:raise BatchError('FALSIFIED_GLOBAL_CROSSING')
    if receipt.get('interpretation') != ('SURFACE_TRIANGLE_CROSSINGS_OBSERVED' if found_cross else 'NO_CROSSINGS_IN_SAMPLED_FRAMES_ONLY'):raise BatchError('FALSIFIED_INTERPRETATION')
    return True

def assemble(parts):
    if type(parts) not in (list,tuple) or not parts:raise BatchError('NO_PARTS')
    for d in parts:validate(d)
    exemplar=parts[0]
    if any(d['source_sha256']!=exemplar['source_sha256'] or d.get('backend')!=exemplar.get('backend') for d in parts):raise BatchError('SOURCE_OR_BACKEND_DRIFT')
    if any(d.get(k)!=exemplar.get(k) for d in parts for k in FALSE_KEYS):raise BatchError('GATE_DRIFT')
    frames=[];actors={a:{'slots':{s:[] for s in SLOTS}} for a in ACTORS}
    for d in parts:
        frames.extend(d['frames'])
        for a in ACTORS:
            for s in SLOTS:actors[a]['slots'][s].extend(d['actors'][a]['slots'][s])
    if frames!=FULL:raise BatchError('NOT_COMPLETE_73_POSE_SET')
    for a in ACTORS:actors[a]['any_crossings']=any(
        row['triangle_contact_pairs']>0 for rows in actors[a]['slots'].values() for row in rows)
    crossing=any(actors[a]['any_crossings'] for a in ACTORS)
    receipt={k:exemplar[k] for k in ('schema','source_sha256','backend',*FALSE_KEYS)}
    receipt.update({'frames':frames,'frame_count':73,'actors':actors,'any_crossings':crossing,
         'interpretation':'SURFACE_TRIANGLE_CROSSINGS_OBSERVED' if crossing else 'NO_CROSSINGS_IN_SAMPLED_FRAMES_ONLY'})
    validate(receipt)
    return receipt

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--part',type=Path,action='append',required=True)
    ap.add_argument('--out',type=Path,required=True);x=ap.parse_args()
    if x.out.exists() or x.out.resolve() in {p.resolve() for p in x.part}:raise BatchError('NO_OVERWRITE')
    chunks=[json.loads(p.read_text()) for p in x.part]
    combined=assemble(chunks)
    combined['partition_sha256']=[hashlib.sha256(p.read_bytes()).hexdigest() for p in x.part]
    x.out.write_text(json.dumps(combined,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'source_sha256':combined['source_sha256'],'frames':73,
        'pairs':{a:{s:sum(x['triangle_contact_pairs'] for x in rows) for s,rows in v['slots'].items()} for a,v in combined['actors'].items()},'scientific_accepted':False},sort_keys=True))
if __name__=='__main__':main()
