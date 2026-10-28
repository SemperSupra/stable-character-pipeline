"""Original-public 410Hz mono PCM and Go W3c source-canonical schedule.

One fixed one-second-ish window (47*1024 samples) per original DoE case.
This is deliberately not a steady-state or human-listening qualification.
"""
import hashlib,json,math,struct,sys,wave
from pathlib import Path
if len(sys.argv)!=3:raise SystemExit('usage: prepare_native_42.py DOE.json OUT_DIR')
doe=json.loads(Path(sys.argv[1]).read_text())
if doe['schema']!='spatial_audio.offaxis_doe.v1' or len(doe['cases'])!=42:
    raise ValueError('unqualified Go source geometry')
if doe['sample_rate_hz']!=48000 or any(x['ebu_gain_status']!='NOT_MEASURED' or x['videolan_pcm_status']!='NOT_MEASURED' for x in doe['cases']):
    raise ValueError('false upstream native acceptance')
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
blocks_per_case=47
block=1024
with (out/'w3c_cases.tsv').open('w') as case, (out/'w3c_videolan_blocks.tsv').open('w') as plan:
    for i,x in enumerate(doe['cases']):
        az=x['relative_azimuth_deg'];el=x['elevation_deg'];yaw=x['listener_yaw_deg']
        assert x['distance_m']==10 and x['layouts']==['surround_5_1','surround_7_1']
        case.write(f"{x['id']}\t{az:.9f}\t{el:.9f}\t{yaw:.9f}\n")
        for j in range(blocks_per_case):
            plan.write(f"{(i*blocks_per_case+j)*block}\t{block}\t{az:.9f}\t{el:.9f}\t10\n")
count=len(doe['cases'])*blocks_per_case*block
# 410Hz, 0.15 amplitude, source rights = original programmatic generation.
with wave.open(str(out/'original_410hz.wav'),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000)
    payload=bytearray()
    for i in range(count):
        q=int(round(32767*.15*math.sin(2*math.pi*410*i/48000)))
        payload+=struct.pack('<h',q)
    w.writeframes(bytes(payload))
manifest={'schema':'spatial_audio/w3c_native_source/1','classification':'ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC',
          'doe_sha256':hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),
          'case_table_sha256':hashlib.sha256((out/'w3c_cases.tsv').read_bytes()).hexdigest(),
          'source_wav_sha256':hashlib.sha256((out/'original_410hz.wav').read_bytes()).hexdigest(),
          'frames':count,'channels':1,'rate':48000,'blocks_per_case':blocks_per_case,
          'upstream_libear':'2db69f8fcea0bc5db8a78e14a9c2ae6ed4283c15',
          'upstream_videolan':'d149ed9744fd399b835c6f2920511f8cbcfce5ea'}
(out/'source_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print('SPATIAL_W3C_SOURCE_PIN_PASS',json.dumps(manifest,sort_keys=True))
