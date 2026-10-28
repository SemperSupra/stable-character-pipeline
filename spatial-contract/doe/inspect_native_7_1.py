"""W3c W2: quantitative 7.1 channel gain parity, separate from W1 observation.

Predeclared per-normalized-speaker abs tolerance 0.005 from earlier native
EBU-vs-VideoLAN ±70-degree experiment (spatial PR #25).
Does not establish waveform/phase/perception, real room or speaker placement.
"""
import hashlib,json,math,struct,sys
from pathlib import Path

TOLERANCE=0.005
LAYOUT=['M+030','M-030','M+000','LFE1','M+090','M-090','M+135','M-135']

def normalized_differences(native_rms,ebu_gains):
    if len(native_rms)!=8 or len(ebu_gains)!=8:
        raise ValueError('wrong 7.1 channel count')
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in native_rms+ebu_gains):
        raise ValueError('nonfinite/negative channel')
    if native_rms[3]>.001 or abs(ebu_gains[3])>1e-6:
        raise ValueError('unqualified LFE routing')
    a=math.sqrt(sum(v*v for i,v in enumerate(native_rms) if i!=3))
    b=math.sqrt(sum(v*v for i,v in enumerate(ebu_gains) if i!=3))
    if a<1e-7 or b<1e-7:
        raise ValueError('silent gain')
    return [None if i==3 else abs(native_rms[i]/a-ebu_gains[i]/b) for i in range(8)]

def main():
    if len(sys.argv)!=5:
        raise SystemExit('usage: inspect_native_7_1.py W1_JSON EBU_NATIVE_TSV VIDEO_7_1_FLOAT_WAV OUT_JSON')
    w1=json.loads(Path(sys.argv[1]).read_text())
    if (w1.get('schema')!='spatial_audio/w3c_native_partial_observations/1'
       or w1.get('case_count')!=42 or
       w1.get('source_rights')!='ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC'
       or w1.get('videolan_42_cases_7_1')!='NOT_MEASURED'):
        raise ValueError('W1 unadmitted or already claimed 7.1')
    cases=w1['cases']
    ebu={}
    for line in Path(sys.argv[2]).read_text().splitlines():
        p=line.split('\t')
        if len(p)!=7:raise ValueError('malformed EBU source response')
        id,profile,az,el,yaw,direct,diffuse=p
        key=(id,profile)
        if key in ebu:raise ValueError('duplicate EBU source row')
        ebu[key]=[float(x) for x in direct.split(',')]
    if len(ebu)!=84:raise ValueError('incomplete EBU direct gain source')
    native=Path(sys.argv[3]).read_bytes()
    count=42*47*1024
    if (native[:4]!=b'RIFF' or native[8:16]!=b'WAVEfmt ' or
        native[36:40]!=b'data' or len(native)!=44+count*8*4 or
        struct.unpack_from('<HHIIHH',native,20)!=(3,8,48000,48000*8*4,32,32) or
        struct.unpack_from('<I',native,40)[0]!=count*8*4):
        raise ValueError('invalid 7.1 float WAV header/layout/size')
    samples=[]
    for i,c in enumerate(cases):
        id=c['id']; gain=ebu[(id,'surround_7_1')]
        start=44+((i+1)*47-1)*1024*8*4
        audio=native[start:start+1024*8*4]
        sums=[0.0]*8;peak=0.0
        for j,(x,) in enumerate(struct.iter_unpack('<f',audio)):
            if not math.isfinite(x):raise ValueError('native 7.1 NaN/Inf')
            peak=max(peak,abs(x))
            sums[j%8]+=x*x
        rms=[math.sqrt(z/1024) for z in sums]
        if peak>1.0:raise ValueError('native 7.1 clipping')
        errors=normalized_differences(rms,gain)
        max_error=max(e for e in errors if e is not None)
        samples.append({'id':id,'relative_azimuth_deg':c['azimuth_deg'],
                        'elevation_deg':c['elevation_deg'],'listener_yaw_deg':c['yaw_deg'],
                        'videolan_7_1_last_1024_rms':rms,
                        'ebu_7_1_direct_gains':gain,
                        'normalized_channel_abs_differences':errors,
                        'maximum_normalized_channel_error':max_error,
                        'meets_prior_0_005_angular_gain_tolerance':max_error<=TOLERANCE})
    overall=max(x['maximum_normalized_channel_error'] for x in samples)
    verdict=all(x['meets_prior_0_005_angular_gain_tolerance'] for x in samples)
    result={'schema':'spatial_audio/w3c_native_7_1_gain_parity/1',
            'status':'PASS_SOURCE_BOUND_7_1_NORMALIZED_GAIN_PARITY' if verdict else 'FAIL_7_1_GAIN_PARITY',
            'w1_source_wav_sha256':w1['source_wav_sha256'],
            'w1_source_doe_sha256':w1['source_doe_sha256'],
            'native_7_1_wav_sha256':hashlib.sha256(native).hexdigest(),
            'speaker_order':LAYOUT,'case_count':42,
            'prior_source_5_1_tolerance':TOLERANCE,
            'max_error_normalized_unit_gain':overall,
            'source_rights':'ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC',
            'real_room_acoustics':'NOT_TESTED','waveform_or_phase_parity':'NOT_ESTABLISHED',
            'speaker_crosstalk':'NOT_TESTED','headphone_compatibility':'NOT_TESTED',
            'native_direct_stereo':'QUARANTINED_NAN','samples':samples}
    Path(sys.argv[4]).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('SPATIAL_W3C_W2_NATIVE_7_1',json.dumps({k:v for k,v in result.items() if k!='samples'},sort_keys=True))
    if not verdict:raise SystemExit('W3c 7.1 true native normalized-gain parity mismatch; no pass')
if __name__=='__main__':main()
