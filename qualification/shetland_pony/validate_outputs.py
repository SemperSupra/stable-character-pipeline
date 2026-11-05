#!/usr/bin/env python3
"""Independent stdlib artifact verifier for public-original Shetland GHA assets."""
import hashlib, json, struct, sys
from pathlib import Path

def check_glb(path):
 b=path.read_bytes()
 assert b[:4]==b'glTF' and struct.unpack_from('<I',b,4)[0]==2, 'glTF 2 header'
 assert struct.unpack_from('<I',b,8)[0]==len(b), 'GLB byte length'
 length,kind=struct.unpack_from('<II',b,12)
 assert kind==0x4E4F534A, 'JSON chunk type'
 data=json.loads(b[20:20+length].decode('utf-8').strip())
 assert data.get('asset',{}).get('version')=='2.0'
 skins=data.get('skins',[])
 assert skins, 'missing skin'
 bone_count=max(len(x.get('joints',[])) for x in skins)
 assert bone_count>=26, f'only {bone_count} rig joints'
 assert data.get('animations'), 'no glTF animation'
 channels=sum(len(x.get('channels',[])) for x in data['animations'])
 assert channels>=8, f'only {channels} channels'
 weighted=sum('JOINTS_0' in prim.get('attributes',{}) and 'WEIGHTS_0' in prim.get('attributes',{})
              for mesh in data.get('meshes',[]) for prim in mesh.get('primitives',[]))
 assert weighted>=2, f'only {weighted} skinned mesh primitives'
 return {'joints':bone_count,'channels':channels,'skinned_primitives':weighted,'mesh_count':len(data['meshes'])}

def run(directory):
 root=Path(directory)
 receipt=json.loads((root/'manifest.json').read_text())
 assert receipt['tool']=='native_blender_shetland_ghcr'
 assert set(receipt['coat_results'])=={'black','pinto','white'}
 results={}
 for coat in ('black','pinto','white'):
  stem='shetland_'+coat+'_ghcr'
  for ext in ('.blend','.glb','.png'):
   p=root/(stem+ext)
   assert p.is_file() and p.stat().st_size>512, f'missing or too small: {p}'
   observed=hashlib.sha256(p.read_bytes()).hexdigest()
   assert observed==receipt['coat_results'][coat][p.name]['sha256'], f'checksum mismatch {p}'
   assert p.stat().st_size==receipt['coat_results'][coat][p.name]['bytes']
  assert (root/(stem+'.blend')).read_bytes().startswith(b'BLENDER')
  png=(root/(stem+'.png')).read_bytes()
  assert png[:8]==b'\x89PNG\r\n\x1a\n'
  assert struct.unpack('>II',png[16:24])==(640,420)
  results[coat]=check_glb(root/(stem+'.glb'))
  print(coat,results[coat],flush=True)
 verdict={'verdict':'PUBLIC_ORIGINAL_NATIVE_STRUCTURAL_PASS','blender':receipt['blender'],'coats':results,
          'limitation':'Synthetic procedural derivative, NOT byte-identical to locally generated reference-derived v1; biomechanical and visual accuracy unqualified'}
 (root/'independent_validation.json').write_text(json.dumps(verdict,indent=2,sort_keys=True)+'\n')
 print(json.dumps(verdict,sort_keys=True))
 return verdict

if __name__=='__main__':
 assert len(sys.argv)==2
 run(sys.argv[1])
