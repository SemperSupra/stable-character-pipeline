"""Independent decode of true native SDL3_mixer offline audio, no SDL dependencies."""
import array
import hashlib
import json
import math
import struct
import sys
import wave
from pathlib import Path

FRAMES=4096
CHANNELS=2
CASES=("fresh_y1","stale_y_update","fresh_y5","positive_x_update")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(path):
    data=Path(path).read_bytes()
    if len(data)!=FRAMES*CHANNELS*4 or sys.byteorder!="little":
        raise ValueError("invalid native float PCM framing")
    pcm=array.array("f")
    pcm.frombytes(data)
    if len(pcm)!=FRAMES*CHANNELS or not all(math.isfinite(x) and abs(x)<=1 for x in pcm):
        raise ValueError("nonfinite/clipped source")
    energy=sum(x*x for x in pcm)
    if energy<1e-9:raise ValueError("silent native SDL mixer")
    return pcm,energy
def observe(root,out):
    root=Path(root)
    src=root/"original_sdl410.wav"
    with wave.open(str(src),"rb") as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())!=(1,2,48000,8192):
            raise ValueError("original source malformed")
        data=w.readframes(8192)
        if not any(data):raise ValueError("source silent")
    outputs={}
    result=dict(schema="spatial_audio/sdl3_full_native_pcm_bug/1",
                rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
                sdl_sha="829a65d769d935c4852f8159e964312c0957260a",
                sdl_mixer_sha="d9478014cddcf00f035c950637917d2280a67ab2",
                original_source_sha256=sha(src),cases=[],failures=[],
                classification="FULL_ORIGINAL_LIBRARY_NATIVE_REAL_PCM_NOT_UPSTREAM_PATCH")
    for name in CASES:
        pcm,energy=decode(root/(name+".f32"))
        outputs[name]=pcm
        result["cases"].append(dict(name=name,energy=energy,
                                  output_sha256=sha(root/(name+".f32"))))
    original=outputs["fresh_y1"]
    stale=outputs["stale_y_update"]
    new=outputs["fresh_y5"]
    positive=outputs["positive_x_update"]
    max_stale=max(abs(a-b) for a,b in zip(original,stale))
    rms_diff_new=math.sqrt(sum((a-b)**2 for a,b in zip(original,new))/len(original))
    rms_diff_x=math.sqrt(sum((a-b)**2 for a,b in zip(original,positive))/len(original))
    result.update(max_pcm_error_stale_vs_y1=max_stale,
                  rms_pcm_delta_fresh_y5=rms_diff_new,
                  rms_pcm_delta_x_changed=rms_diff_x,
                  frozen_max_stale_error=1e-5,
                  frozen_min_real_position_difference=0.001)
    if max_stale>1e-5:result["failures"].append("stale_case_changed_pcm")
    if rms_diff_new<=0.001:result["failures"].append("fresh_y_position_not_audible")
    if rms_diff_x<=0.001:result["failures"].append("x_positive_control_not_audible")
    result["status"]="PASS_EXPECTED_NATIVE_BUG_REPRODUCED" if not result["failures"] else "FAIL"
    Path(out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("SDL3_FULL_NATIVE_INDEPENDENT_PCM",result["status"],
          "stale",max_stale,"fresh_delta",rms_diff_new,"x_delta",rms_diff_x)
    if result["status"]=="FAIL":
        raise ValueError("SDL3 full-native preregistered regression failed")
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: sdl3_full_native_observe.py SRC_DIR OUT_JSON")
    observe(sys.argv[1],sys.argv[2])
