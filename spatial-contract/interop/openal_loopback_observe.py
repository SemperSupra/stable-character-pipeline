"""Independent strict float32 readback of actual OpenAL Soft loopback output."""
import array
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

FRAMES=8192
RATE=48000
RIGHTS="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"
UPSTREAM="b7463649fd73188146e3b1467a91e7f0926a6d04"
LAYOUTS={"stereo":2,"surround_5_1":6,"surround_7_1":8}
POSES={"left":(-10.0,0.0,-10.0),"right":(10.0,0.0,-10.0),"front":(0.0,0.0,-10.0)}
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def decode(buf,n):
    if sys.byteorder!="little" or len(buf)!=n*FRAMES*4:
        raise ValueError("wrong output byte order, count or shape")
    data=array.array("f")
    data.frombytes(buf)
    if len(data)!=n*FRAMES or not all(math.isfinite(v) and abs(v)<=1.0 for v in data):
        raise ValueError("nonfinite or clipped actual output")
    energy=[0.0]*n
    peaks=[0.0]*n
    onset=None
    for i in range(FRAMES):
        for ch in range(n):
            v=data[i*n+ch]
            energy[ch]+=v*v
            peaks[ch]=max(peaks[ch],abs(v))
            if onset is None and abs(v)>1e-7:
                onset=i
    if onset is None or sum(energy)<1e-10:
        raise ValueError("native source became silent")
    return dict(total_energy=sum(energy),energy_by_channel=energy,peak=max(peaks),
                peak_by_channel=peaks,first_detected_frame=onset,
                f32_buffer_sha256=hashlib.sha256(buf).hexdigest())

def observe(root,out):
    root=Path(root)
    source=root/"input_48000_s16le.raw"
    payload=source.read_bytes()
    if len(payload)!=FRAMES*2 or struct.unpack_from("<h",payload,0)[0]!=14745 or any(payload[2:]):
        raise ValueError("wrong original input 48k PCM16 mono or corrupt source")
    result=dict(schema="spatial_audio/openal_soft_loopback_qualification/1",rights=RIGHTS,
                renderer_commit=UPSTREAM,source_sha256=sha(source),
                source_frames=FRAMES,source_sample_rate_hz=RATE,
                channel_orders="PROVIDER_SPECIFIC_UNQUALIFIED",
                observed=[],negative_controls=["full_buffer_length","finite","peak","non_silent","right_left_ear_preference"],
                separate_capabilities_not_tested=["HRTF","room_reflections","head_tracking","Doppler","height","human_audition"])
    for layout,n in LAYOUTS.items():
        records={}
        for pose,coords in POSES.items():
            name=layout+"_"+pose+".f32"
            data=decode((root/name).read_bytes(),n)
            data.update(layout=layout,pose=pose,xyz=coords,channel_count=n)
            records[pose]=data
            result["observed"].append(data)
        if records["left"]["f32_buffer_sha256"]==records["right"]["f32_buffer_sha256"]:
            raise ValueError("source positions did not alter real audio for "+layout)
        if layout=="stereo":
            l=records["left"]["energy_by_channel"]
            r=records["right"]["energy_by_channel"]
            if not (l[0]>l[1]*1.25 and r[1]>r[0]*1.25):
                raise ValueError("expected distinct left/right stereo positional output")
    result["status"]="PASS_NATIVE_OUTPUT_VERIFIED"
    Path(out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("OPENAL_NATIVE_INDEPENDENT_PCM_PASS",len(result["observed"]),
          "outputs source_sha256="+result["source_sha256"])
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: openal_loopback_observe.py NATIVE_DATA_DIR OUT.json")
    observe(sys.argv[1],sys.argv[2])
