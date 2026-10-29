"""Independent original-source and actual HRTF pose-change full PCM observer."""
import array
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
FRAMES,CHANNELS,RATE=8192,2,48000
NAMES=("static_left","static_right","source_switch","listener_switch")
TOL=1e-6
MIN_RMS_DIFFERENCE=1e-5
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pcm(path):
    buf=Path(path).read_bytes()
    if sys.byteorder!="little" or len(buf)!=FRAMES*CHANNELS*4:raise ValueError("bad source PCM shape")
    x=array.array("f");x.frombytes(buf)
    if len(x)!=FRAMES*CHANNELS or any(not math.isfinite(v) or abs(v)>1 for v in x):
        raise ValueError("unbounded or nonfinite PCM")
    if sum(v*v for v in x)<1e-8:raise ValueError("silent PCM")
    return x
def rms_delta(a,b,first,last):
    return math.sqrt(sum((a[i]-b[i])**2 for i in range(first*CHANNELS,last*CHANNELS))/
        ((last-first)*CHANNELS))
def observe(root,out):
    root=Path(root)
    source=(root/"original_mono_410_s16le.raw").read_bytes()
    if len(source)!=FRAMES*2:raise ValueError("source bytes not actual 8192 PCM16 frames")
    for i in (0,1,255,1023,1024,2048,4095,8191):
        actual=struct.unpack_from("<h",source,i*2)[0]
        expected=int(round(.12*math.sin(2*math.pi*410*i/RATE)*32767))
        if abs(actual-expected)>1:raise ValueError("original 410Hz source drift")
    rows={}
    for row in (root/"hrtf_motion_states.tsv").read_text().splitlines():
        parts=row.split("\t")
        if len(parts)!=5:raise ValueError("wrong native state columns")
        name,status,frames,peak,energy=parts
        if name not in NAMES or name in rows or status!="1" or int(frames)!=FRAMES or not(0<float(peak)<=1) or float(energy)<=1e-8:
            raise ValueError("native HRTF not actually enabled or malformed")
        rows[name]=dict(hrtf_status=int(status),peak=float(peak),energy=float(energy))
    if set(rows)!=set(NAMES):raise ValueError("missing native render")
    data={name:pcm(root/(name+".f32")) for name in NAMES}
    if data["static_left"].tobytes()==data["static_right"].tobytes():
        raise ValueError("no left/right HRTF distinction")
    comparisons=[]
    for mode in ("source_switch","listener_switch"):
        original=data["static_left"]
        moved=data[mode]
        prefix=max(abs(a-b) for a,b in zip(original[:2048*CHANNELS],moved[:2048*CHANNELS]))
        mid=rms_delta(original,moved,2048,4096)
        late=rms_delta(original,moved,6144,8192)
        seams=[max(abs(moved[i*CHANNELS+c]-moved[(i-1)*CHANNELS+c]) for c in range(CHANNELS))
            for i in (2048,4096,6144)]
        comparisons.append(dict(mode=mode,prefix_max_abs_difference=prefix,
            mid_rms_difference=mid,late_rms_difference=late,block_seam_max_steps=seams))
        if prefix>TOL or max(mid,late)<=MIN_RMS_DIFFERENCE:
            raise ValueError("frozen HRTF moving-source/listener response falsified "+mode)
    receipt=dict(schema="spatial_audio/openal_native_hrtf_motion/1",
        status="PASS_BLOCK_CONTROL_HRTF_QUALIFIED",
        provider_sha="b7463649fd73188146e3b1467a91e7f0926a6d04",
        rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
        source_sha256=hashlib.sha256(source).hexdigest(),rate=RATE,frames=FRAMES,
        hop=1024,output_channels=CHANNELS,
        cases=[dict(mode=n,output_sha256=sha(root/(n+".f32")),**rows[n]) for n in NAMES],
        comparisons=comparisons,prefix_tolerance=TOL,
        moving_rms_threshold=MIN_RMS_DIFFERENCE,
        not_qualified=["SAMPLE_CONTINUOUS_MOVEMENT","ROOM","DOPPLER",
            "PERSONALIZED_HRTF","LISTENING","SPEAKER_LATENCY","BRIR"])
    Path(out).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("OPENAL_HRTF_MOVEMENT_OBSERVER_PASS renders",len(NAMES),"comparisons",len(comparisons))
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: openal_hrtf_motion_observe.py ORIGINAL_DIR OUTPUT.json")
    observe(sys.argv[1],sys.argv[2])
