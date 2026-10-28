"""Independent source-linked native EBU-gain/VideoLAN-5.1 PCM observer.

Do not equate instantaneous gain with time-domain gain after panner smoothing.
Reported per-case differences are observations, NOT DSP parity acceptance.
"""
import hashlib,json,math,struct,sys,wave
from pathlib import Path
if len(sys.argv)!=5:raise SystemExit('usage: inspect_native_42.py DOE.json DIR EBU_TSV VIDEOLAN_FLOAT_WAV')
d=Path(sys.argv[2]); m=json.loads((d/'source_manifest.json').read_text())
doe_raw=Path(sys.argv[1]).read_bytes();doe=json.loads(doe_raw)
ebu=Path(sys.argv[3]);v=Path(sys.argv[4])
if hashlib.sha256(doe_raw).hexdigest()!=m['doe_sha256']:raise ValueError('DOE source changed')
if hashlib.sha256((d/'original_410hz.wav').read_bytes()).hexdigest()!=m['source_wav_sha256']:raise ValueError('source wave changed')
if hashlib.sha256((d/'w3c_cases.tsv').read_bytes()).hexdigest()!=m['case_table_sha256']:raise ValueError('source case table changed')
rows={}
for line in ebu.read_text().splitlines():
    parts=line.split('\t')
    if len(parts)!=7:raise ValueError('malformed native EBU output')
    id,layout,az,el,yaw,da,di=parts
    if (id,layout) in rows:raise ValueError('duplicate native EBU result')
    direct=[float(x) for x in da.split(',')];diffuse=[float(x) for x in di.split(',')]
    n=6 if layout=='surround_5_1' else 8 if layout=='surround_7_1' else 0
    if not n or len(direct)!=n or len(diffuse)!=n or not all(math.isfinite(x) for x in direct+diffuse):
        raise ValueError('bad EBU size/finite')
    if abs(direct[3])>1e-6 or abs(diffuse[3])>1e-6:raise ValueError('EBU LFE source routed')
    rows[(id,layout)]=(float(az),float(el),float(yaw),direct,diffuse)
if len(rows)!=84:raise ValueError('incomplete EBU gain table')
raw=v.read_bytes()
count=m['frames']
if (len(raw)!=44+count*6*4 or raw[0:4]!=b'RIFF' or raw[8:16]!=b'WAVEfmt ' or
    struct.unpack_from('<HHIIHH',raw,20)!=(3,6,48000,48000*6*4,24,32) or
    raw[36:40]!=b'data' or struct.unpack_from('<I',raw,40)[0]!=count*6*4):
    raise ValueError('wrong native VideoLAN 5.1 PCM header/sample count/layout')
blocks=m['blocks_per_case']
if count!=42*blocks*1024:raise ValueError('unexpected sample clocks')
outputs=[]
for i,c in enumerate(doe['cases']):
    id=c['id']
    vals={}
    for layout in ('surround_5_1','surround_7_1'):
        az,el,yaw,ga,di=rows[(id,layout)]
        if (abs(az-c['relative_azimuth_deg'])>1e-6 or
            abs(el-c['elevation_deg'])>1e-6 or
            abs(yaw-c['listener_yaw_deg'])>1e-6):
            raise ValueError('EBU native case order/geometry drift')
        vals[layout]={'ebu_direct':ga,'ebu_diffuse':di,'ebu_native_status':'MEASURED'}
    # Observe LAST 1024 samples in each case's 47-block native renderer
    # sequence. This limits, but does not eliminate, smoothing contamination.
    start=((i+1)*blocks-1)*1024*6*4+44
    window=raw[start:start+1024*6*4]
    sums=[0.0]*6;maxabs=0.0
    for (j,(x,)) in enumerate(struct.iter_unpack('<f',window)):
        if not math.isfinite(x):raise ValueError('VideoLAN NaN/Inf')
        maxabs=max(maxabs,abs(x));sums[j%6]+=x*x
    rms=[math.sqrt(s/1024) for s in sums]
    if maxabs>1.0 or max(rms)<1e-6:raise ValueError('native VideoLAN silent/clipped')
    if rms[3]>.001:raise ValueError('native VideoLAN LFE unexpected')
    direct=vals['surround_5_1']['ebu_direct']
    power=math.sqrt(sum(x*x for j,x in enumerate(direct) if j!=3))
    observed=math.sqrt(sum(x*x for j,x in enumerate(rms) if j!=3))
    gain_differences=[abs(rms[j]/observed-direct[j]/power) if j!=3 else None for j in range(6)]
    outputs.append({'id':id,'azimuth_deg':c['relative_azimuth_deg'],
                    'elevation_deg':c['elevation_deg'],'yaw_deg':c['listener_yaw_deg'],
                    'ebu':vals,
                    'videolan_5_1_pcm_rms_last_1024':rms,
                    'videolan_5_1_pcm_status':'MEASURED',
                    'videolan_7_1_pcm_status':'NOT_MEASURED',
                    'normalized_5_1_gain_abs_differences_NOT_ACCEPTANCE':gain_differences})
result={'schema':'spatial_audio/w3c_native_partial_observations/1',
        'classification':'NATIVE_SAME_SOURCE_MEASURED_NOT_PSYCHOACOUSTIC_OR_DSP_PARITY',
        'status':'PASS_COMPLETENESS_AND_FINITE_OBSERVATIONS',
        'source_wav_sha256':m['source_wav_sha256'],
        'source_doe_sha256':m['doe_sha256'],
        'source_revisions':{'ebu':m['upstream_libear'],'videolan':m['upstream_videolan']},
        'ebu_42_cases_5_1':'MEASURED','ebu_42_cases_7_1':'MEASURED',
        'videolan_42_cases_5_1':'MEASURED','videolan_42_cases_7_1':'NOT_MEASURED',
        'stereo_direct_native':'QUARANTINED_NAN','panner_equivalence':'NOT_ESTABLISHED',
        'audio_subjective_listening':'NOT_TESTED','source_rights':'ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC',
        'case_count':len(outputs),'cases':outputs}
(d/'w3c_native_observations.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print('SPATIAL_W3C_NATIVE_PARTIAL_REAL_PASS',json.dumps({k:x for k,x in result.items() if k!='cases'},sort_keys=True))
