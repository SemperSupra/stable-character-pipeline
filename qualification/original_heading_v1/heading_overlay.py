#!/usr/bin/env python3
"""Non-destructive, source-hash-bound glTF heading correction for two authored fictional actors.
No vendor or human identity source, gait/contact acceptance, or release grant is implied.
"""
from __future__ import annotations
import argparse, hashlib, json, math, struct
from pathlib import Path

class Reject(Exception): pass

def insist(ok: bool, code: str) -> None:
    if not ok: raise Reject(code)

def decode(raw: bytes) -> tuple[dict, bytes]:
    insist(len(raw)>=28 and raw[:4]==b'glTF', 'GLB_BAD_HEADER')
    _,version,total=struct.unpack_from('<4sII',raw)
    insist(version==2 and total==len(raw),'GLB_BAD_LENGTH')
    n,kind=struct.unpack_from('<I4s',raw,12)
    insist(kind==b'JSON' and n>0 and 20+n+8<=len(raw), 'GLB_BAD_JSON_CHUNK')
    try: doc=json.loads(raw[20:20+n])
    except (ValueError,UnicodeDecodeError) as e:raise Reject('GLB_BAD_JSON') from e
    off=20+n;size,kind=struct.unpack_from('<I4s',raw,off)
    insist(kind==b'BIN\0' and off+8+size==len(raw),'GLB_BAD_BINARY_CHUNK')
    return doc,raw[off+8:]

def produce(input_path:Path, output_path:Path, receipt_path:Path, expected_sha256:str)->dict:
    a=input_path.resolve();b=output_path.resolve();c=receipt_path.resolve()
    insist(a!=b and a!=c and b!=c,'PATHS_MUST_BE_DISTINCT')
    raw=a.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    insist(len(expected_sha256)==64 and digest==expected_sha256.lower(),'SOURCE_SHA256_MISMATCH')
    doc,binary=decode(raw)
    insist(doc.get('asset',{}).get('version')=='2.0','GLTF_VERSION')
    e=doc.get('extras',{})
    insist(e.get('source_class')=='ORIGINAL_SELF_AUTHORED_SYNTHETIC' and e.get('third_party_models') is False,'SOURCE_NOT_ORIGINAL_FICTIONAL')
    skins=doc.get('skins',[])
    insist(len(skins)==2 and all(len(s.get('joints',[]))==17 for s in skins),'EXPECTED_SKINS_MISSING')
    pairs=(('AsterOriginal_SceneRoot',-90),('JuniperOriginal_SceneRoot',90))
    names={};
    for i,n in enumerate(doc.get('nodes',[])):
        if n.get('name') in [p[0] for p in pairs]:
            insist(n['name'] not in names,'DUPLICATE_SOURCE_ROOT')
            names[n['name']]=i
    insist(len(names)==2,'MISSING_SOURCE_ROOT')
    animations=doc.get('animations',[])
    insist(len(animations)==1 and len(animations[0].get('channels',[]))>=20,'EXPECTED_ANIMATION_MISSING')
    for name,_ in pairs:
        i=names[name];n=doc['nodes'][i]
        insist('rotation' not in n and 'matrix' not in n,'ROOT_ALREADY_ROTATED')
        channels=[c for c in animations[0]['channels'] if c.get('target',{}).get('node')==i]
        insist(any(c['target'].get('path')=='translation' for c in channels),'MISSING_ROOT_TRANSLATION')
        insist(not any(c['target'].get('path')=='rotation' for c in channels),'ROOT_ROTATION_ANIMATED')
    for name,deg in pairs:
        angle=math.radians(deg)/2
        doc['nodes'][names[name]]['rotation']=[0.0,math.sin(angle),0.0,math.cos(angle)]
    doc.setdefault('asset',{}).setdefault('extras',{})['r009_heading_alignment_review_v1']={
        'input_sha256':digest, 'operation':'static_root_local_heading_only',
        'root_yaw_degrees':{'AsterOriginal':-90,'JuniperOriginal':90},
        'approach_axis':'+X for Aster, -X for Juniper',
        'source_front_axis':'local -Z','rights':'OWNER_CONTROLLED_NO_PUBLISH_GRANT',
        'source_original_unchanged':True,'motion_or_identity_accepted':False}
    jb=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    jb+=b' '*((-len(jb))%4)
    binary+=b'\0' * ((-len(binary))%4)
    encoded=struct.pack('<4sII',b'glTF',2,12+8+len(jb)+8+len(binary))+struct.pack('<I4s',len(jb),b'JSON')+jb+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    # No direct source overwrite; prepare before atomic output rename.
    newdoc,newbin=decode(encoded)
    insist(newbin==decode(raw)[1] and len(newdoc['animations'][0]['channels'])==len(animations[0]['channels']),'ANIMATION_BINARY_CHANGED')
    insist(len(newdoc['skins'])==2 and len(newdoc['meshes'])==len(doc['meshes']),'MESH_OR_SKINS_CHANGED')
    output_path.parent.mkdir(parents=True,exist_ok=True)
    tmp=output_path.with_name(output_path.name+'.tmp');tmp.write_bytes(encoded);tmp.replace(output_path)
    r={'schema':'scp.r009.original-heading-alignment.v1','source_sha256':digest,
       'derived_sha256':hashlib.sha256(encoded).hexdigest(), 'source_unchanged':True,
       'changed_root_rotations_only':True,'animation_binary_unchanged':True,
       'source_fictional_original':True,'joints_each':[len(s['joints']) for s in skins],
       'heading_yaw_degrees':{'AsterOriginal':-90,'JuniperOriginal':90},
       'gait_contact':'NOT_QUALIFIED','human_approval':False,'publication_approved':False}
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    receipt_path.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    insist(hashlib.sha256(a.read_bytes()).hexdigest()==digest,'SOURCE_CHANGED_DURING_EXECUTION')
    return r

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--receipt',type=Path,required=True);ap.add_argument('--expected-sha256',required=True)
    args=ap.parse_args()
    try: print(json.dumps(produce(args.input,args.output,args.receipt,args.expected_sha256),sort_keys=True))
    except (Reject,OSError,KeyError,struct.error) as e:raise SystemExit('HEADING_OVERLAY_REJECT:'+str(e))
