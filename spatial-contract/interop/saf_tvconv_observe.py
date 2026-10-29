"""Independent actual SAF time-varying convolution source and PCM observer."""
import array
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

FRAMES=8192
HOP=256
NAMES=("static0","static1","switch_012","cycle_012")
PREFIX_TOL=1e-6
DIFFERENCE_MIN=1e-5
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
    raw=Path(path).read_bytes()
    if sys.byteorder!="little" or len(raw)!=FRAMES*4:raise ValueError("not complete original SAF float32")
    samples=array.array("f")
    samples.frombytes(raw)
    if not all(math.isfinite(x) and abs(x)<=1 for x in samples):raise ValueError("nonfinite/peak overflow")
    if sum(x*x for x in samples)<=1e-8:raise ValueError("native output silent")
    return samples
def rms(a,b,start,end):
    return math.sqrt(sum((a[i]-b[i])**2 for i in range(start,end))/(end-start))
def observe(root,out):
    root=Path(root)
    src=(root/"original_410_s16le.raw").read_bytes()
    if len(src)!=FRAMES*2:raise ValueError("original source count")
    for frame in (0,1,255,2048,4096,6143,6144,8191):
        val=struct.unpack_from("<h",src,frame*2)[0]
        reference=0 if frame>=6144 else .1*math.sin(2*math.pi*410*frame/48000)+(.2 if frame in (2048,4096) else 0)
        if abs(val-int(round(reference*32767)))>1:raise ValueError("source is not admitted synthetic")
    data={n:load(root/(n+".f32")) for n in NAMES}
    base=data["static0"]
    switched=data["switch_012"]
    prefix=max(abs(a-b) for a,b in zip(base[:8*HOP],switched[:8*HOP]))
    later=rms(base,switched,8*HOP,24*HOP)
    static_delta=rms(base,data["static1"],8*HOP,24*HOP)
    if prefix>PREFIX_TOL or later<=DIFFERENCE_MIN or static_delta<=DIFFERENCE_MIN:
        raise ValueError("preregistered TVConv fixed-prefix/IR-change difference falsified")
    results=[]
    for name in NAMES:
        a=data[name]
        energy=sum(x*x for x in a)
        tail=sum(x*x for x in a[6144:])
        seams=[abs(a[i]-a[i-1]) for i in (8*HOP,16*HOP,24*HOP)]
        results.append(dict(mode=name,sha256=sha(root/(name+".f32")),
            peak=max(abs(x) for x in a),energy=energy,
            late_source_zero_window_energy=tail,
            ir_switch_seam_steps=seams))
    report=dict(schema="spatial_audio/saf_native_tvconv/1",
        status="PASS_PINNED_NATIVE_IR_SWITCH",
        source_rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
        provider="leomccormack/Spatial_Audio_Framework",
        provider_commit="18fd5aba46e20787b51f28f7197a68506c965c07",
        source_sha256=hashlib.sha256(src).hexdigest(),hop=HOP,frames=FRAMES,
        source_sample_rate=48000,ir_length=512,ir_count=3,
        float32_mono_outputs=len(NAMES),prefix_max_abs_error=prefix,
        switched_vs_static0_rms=later,static1_vs_static0_rms=static_delta,
        frozen_prefix_tolerance=PREFIX_TOL,frozen_min_rms_difference=DIFFERENCE_MIN,
        cases=results,not_tested=["SOFA","PERSONALIZED_HRTF","SAMPLE_CONTINUOUS_3D","ROOM_T60",
            "HUMAN_AUDITION","HEARING","ABSOLUTE_IR_PARITY","DOPPLER"])
    Path(out).write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("SAF_TVCONV_NATIVE_OBSERVER_PASS outputs",len(NAMES),"prefix",prefix,
         "changed",later,"static_filter_difference",static_delta)
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: saf_tvconv_observe.py ORIGINAL_DIR OUT.json")
    observe(sys.argv[1],sys.argv[2])
