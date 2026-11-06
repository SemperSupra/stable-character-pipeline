#!/usr/bin/env python3
"""Independent red-team probes; runs with a generated GLB and its wind trace."""
import argparse, copy, json, pathlib, struct, tempfile, sys
from validate_physical_wind_glb import validate, glb_read, AdmissionError

def refuse(glb,trace):
    try: validate(glb,trace)
    except (AdmissionError, ValueError, KeyError, IndexError, TypeError, struct.error): return True
    return False

def main(glb,trace):
    validate(glb,trace)
    data=bytearray(pathlib.Path(glb).read_bytes()); doc,_=glb_read(glb)
    jlen=struct.unpack_from('<I',data,12)[0]; bin_off=20+jlen+8
    with tempfile.TemporaryDirectory() as d:
        folder=pathlib.Path(d)
        bad_trace=folder/'mutated.json'
        r=json.loads(pathlib.Path(trace).read_text())
        r['samples'][100]['tip_displacement_m']+=.01
        bad_trace.write_text(json.dumps(r))
        assert refuse(glb,bad_trace),'changed unmeasured trace unexpectedly accepted'
        bad_bytes=folder/'weights.glb'
        ac=doc['accessors'][doc['animations'][0]['samplers'][0]['output']]
        pos=bin_off+doc['bufferViews'][ac['bufferView']]['byteOffset']+4*8
        struct.pack_into('<f',data,pos,.999999)
        bad_bytes.write_bytes(data)
        assert refuse(bad_bytes,trace),'tampered animation weight unexpectedly accepted'
        data=bytearray(pathlib.Path(glb).read_bytes())
        ac=doc['accessors'][doc['meshes'][0]['primitives'][0]['targets'][0]['POSITION']]
        pos=bin_off+doc['bufferViews'][ac['bufferView']]['byteOffset']
        # Corrupt enough in one primitive to violate finite validation.
        struct.pack_into('<f',data,pos,float('nan'))
        bad_bytes.write_bytes(data)
        assert refuse(bad_bytes,trace),'nonfinite geometry wrongly accepted'
        dct=copy.deepcopy(doc)
        dct['animations'][0]['extras']['loop']=True
        raw=json.dumps(dct,separators=(',',':')).encode('utf8')
        raw+=b' '*((-len(raw))%4)
        original=pathlib.Path(glb).read_bytes()
        bins=original[bin_off:]
        full=(struct.pack('<4sII',b'glTF',2,12+8+len(raw)+8+len(bins))
             +struct.pack('<II',len(raw),0x4e4f534a)+raw
             +struct.pack('<II',len(bins),0x004e4942)+bins)
        bad_bytes.write_bytes(full)
        assert refuse(bad_bytes,trace),'false looping claim unexpectedly accepted'
    return {'schema':'scp.flora.independent-redteam-physical.v1','passed':4,'controls':['changed wind receipt','changed binary morph weight','nonfinite morph displacement','false-loop glTF metadata']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--glb',required=True);p.add_argument('--wind',required=True)
    x=p.parse_args()
    try: print(json.dumps(main(x.glb,x.wind),indent=2))
    except Exception as e: print('RED_TEAM_FAILED: '+str(e),file=sys.stderr);sys.exit(1)
