"""Independent scientific observer for native Go distance amplitude WAV batches.

Uses Python binary parsing and float64 analytical model, not production Go
attenuation math. Validates every sample of all 85 float32 WAVs.
"""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

RATE, FRAMES = 48000, 2048
DS = (1, 2, 5, 10, 20, 40, 100)
LAYOUTS = (2, 6, 8)
KINDS = ("impulse", "tone")
MODES = ("identity", "inverse_distance")
TOL = 1e-6
SOURCE_RIGHTS = "ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def parse(path,channels,fmt,bits):
    b = Path(path).read_bytes()
    if len(b)<44 or b[:4]!=b"RIFF" or b[8:16]!=b"WAVEfmt " or b[36:40]!=b"data":
        raise ValueError("WAVE header shape")
    size,fmtlen,form,n,rate,byterate,align,depth,bytesize=(
        struct.unpack_from("<I",b,4)[0],
        struct.unpack_from("<I",b,16)[0],
        struct.unpack_from("<H",b,20)[0],
        struct.unpack_from("<H",b,22)[0],
        struct.unpack_from("<I",b,24)[0],
        struct.unpack_from("<I",b,28)[0],
        struct.unpack_from("<H",b,32)[0],
        struct.unpack_from("<H",b,34)[0],
        struct.unpack_from("<I",b,40)[0])
    expected=FRAMES*channels*bits//8
    if (size!=len(b)-8 or fmtlen!=16 or form!=fmt or n!=channels or rate!=RATE or
        byterate!=RATE*channels*bits//8 or align!=channels*bits//8 or depth!=bits or
        bytesize!=expected or len(b)!=44+expected):
        raise ValueError("source WAV frame, channel, format or length mismatch")
    letter="h" if bits==16 else "f"
    output=struct.unpack_from("<"+letter*(FRAMES*channels),b,44)
    if bits==32 and any(not math.isfinite(v) or abs(v)>1 for v in output):
        raise ValueError("nonfinite/clipped float PCM")
    return output

def expected_gain(mode,distance):
    if mode=="identity":return 1.0
    if mode=="inverse_distance":return min(1,10.0/max(distance,1.0))
    raise ValueError("unknown curve")

def inspect(root,out):
    root=Path(root)
    m=json.loads((root/"manifest.json").read_text())
    if (m["schema"]!="spatial_audio/w4c_go_attenuation_batch/1" or
        m["rights"]!=SOURCE_RIGHTS or m["rate"]!=RATE or m["frames"]!=FRAMES or
        m["oracle"]!="INDEPENDENT_FLOAT64_PRESSURE_AMPLITUDE_MIN_1_REFERENCE_10_CLAMP_ONE"):
        raise ValueError("provenance or frozen mathematics drift")
    sources={}
    for kind in KINDS:
        path=root/("original_"+kind+".wav")
        if m["source_sha256"].get(kind)!=sha(path):raise ValueError("mono source SHA mismatch")
        sources[kind]=parse(path,1,1,16)
        # Independent first-party generation checks using rounded expected PCM16.
        for i,actual in enumerate(sources[kind]):
            ideal=(.25 if i==0 else .15 if i==1023 else 0.0) if kind=="impulse" else .125*math.sin(2*math.pi*410*i/RATE)
            if abs(actual-int(round(ideal*32767)))>1:raise ValueError("unexpected source material")
    entries=m["outputs"]
    if len(entries)!=85:raise ValueError("wrong batch size")
    seen=set()
    records=[]
    maximum=0.0
    for item in entries:
        name=item["filename"]
        if name in seen or Path(name).name!=name or name.startswith(".") or "/" in name:
            raise ValueError("duplicate/path traversal")
        seen.add(name)
        mode=item["mode"]
        kind=item["source_kind"]
        n=item["channels"]
        d=item["distance_m"]
        ramp=mode=="sample_linear_ramp_1_to_0.5"
        if kind not in KINDS or n not in LAYOUTS or (not ramp and (mode not in MODES or d not in DS)):
            raise ValueError("unqualified mode/source/distance/layout")
        if ramp and (n!=8 or kind!="tone" or name!="ramp_ch8_tone.wav"):
            raise ValueError("bad ramp metadata")
        expected_filename=("ramp_ch8_tone.wav" if ramp else
            f"{mode}_d{d:03d}_ch{n}_{kind}.wav")
        if name!=expected_filename or item["sha256"]!=sha(root/name) or item["bytes"]!=44+FRAMES*n*4:
            raise ValueError("file/custody mismatch")
        pcm=parse(root/name,n,3,32)
        gain=expected_gain(mode,d) if not ramp else -1
        if item["gain"]!=gain:raise ValueError("declared gain does not match independent oracle")
        if not any(abs(v)>0 for v in pcm):raise ValueError("silent output")
        worst=0.0
        for f in range(FRAMES):
            framegain=(1-.5*f/(FRAMES-1)) if ramp else gain
            for ch in range(n):
                sample=0.0 if n>=6 and ch==3 else float(sources[kind][f])/32768*(.6/(ch+1))
                want=sample*framegain
                err=abs(pcm[f*n+ch]-want)
                worst=max(worst,err)
                if err>TOL:raise ValueError(f"unqualified sample {name} frame={f} ch={ch} err={err}")
        maximum=max(maximum,worst)
        records.append(dict(file=name,mode=mode,distance=d,channels=n,source_kind=kind,
                            max_sample_abs_error=worst,output_sha256=item["sha256"]))
    expected=set(["ramp_ch8_tone.wav"]+
        [f"{mode}_d{d:03d}_ch{n}_{kind}.wav"
         for mode in MODES for d in DS for n in LAYOUTS for kind in KINDS])
    if seen!=expected:raise ValueError("case grid incomplete")
    result=dict(schema="spatial_audio/w4c_independent_observer/1",status="PASS",
                source_manifest_sha256=sha(root/"manifest.json"),total_render_cases=len(records),
                maximum_sample_absolute_error=maximum,tolerance=TOL,
                observed=records,
                excluded=["DELAY","AIR_ABSORPTION","DOPPLER","ROOM_REFLECTIONS",
                          "PERCEPTUAL_DISTANCE","VIDEO_LAN_NATIVE_PHYSICS","SAMPLE_CONTINUOUS_3D_MOTION"])
    Path(out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("W4C_INDEPENDENT_PCM_PASS cases",len(records),"max_abs_error",maximum)
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: observe_distance.py ARTIFACT_DIR OUT.json")
    inspect(sys.argv[1],sys.argv[2])
