"""Independent verification of explicit HRTF on/off for five source poses."""
import array
import hashlib
import json
import math
import sys
from pathlib import Path

FRAMES=8192
POSES=("left","right","front","back","elevated")
STATUS={"on":1,"off":0}
HRTF_DIFF_MIN=1e-5
HRTF_MIN_POSES=3
def pcm(path):
    blob=path.read_bytes()
    if sys.byteorder!="little" or len(blob)!=FRAMES*2*4:
        raise ValueError("invalid stereo float PCM size")
    samples=array.array("f")
    samples.frombytes(blob)
    if len(samples)!=FRAMES*2 or not all(math.isfinite(v) and abs(v)<=1 for v in samples):
        raise ValueError("nonfinite or clipped PCM")
    if sum(v*v for v in samples)<1e-9:raise ValueError("render silent")
    return samples,hashlib.sha256(blob).hexdigest()
def observe(root,out):
    root=Path(root)
    rows={}
    for row in (root/"hrtf_states.tsv").read_text().splitlines():
        parts=row.split("\t")
        if len(parts)!=5:raise ValueError("bad HRTF state evidence")
        mode,pose,state,peak,energy=parts
        if mode not in STATUS or pose not in POSES or (mode,pose) in rows:
            raise ValueError("duplicate/unknown HRTF status")
        if int(state)!=STATUS[mode] or not 0<float(peak)<=1 or float(energy)<=0:
            raise ValueError("renderer silently failed actual HRTF mode")
        rows[mode,pose]=dict(mode=mode,pose=pose,status=int(state),peak=float(peak),energy=float(energy))
    if len(rows)!=10:raise ValueError("incomplete native modes")
    results=dict(schema="spatial_audio/openal_hrtf_batch/1",
        renderer_commit="b7463649fd73188146e3b1467a91e7f0926a6d04",
        rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
        source="SELF_AUTHORED_48000_S16LE_IMPULSE_14745_AT_FRAME_0",
        actual_hrtf_states=rows.values().__class__.__name__,cases=[],comparisons=[],
        hrtf_diff_min=HRTF_DIFF_MIN,min_different_poses=HRTF_MIN_POSES,
        limitations=["NO_PERSONALIZED_HRTF","NO_6DOF","NO_PERCEPTUAL_FRONT_BACK_ACCEPTANCE",
                     "NO_ROOM_OCCLUSION","NO_DEVICE_PLAYBACK"])
    samples={}
    for mode in STATUS:
        for pose in POSES:
            p,h=pcm(root/("hrtf_"+mode+"_"+pose+".f32"))
            samples[mode,pose]=p
            results["cases"].append(dict(**rows[mode,pose],sha256=h))
    different=0
    for pose in POSES:
        a=samples["off",pose]
        b=samples["on",pose]
        delta=math.sqrt(sum((x-y)**2 for x,y in zip(a,b))/len(a))
        if delta>HRTF_DIFF_MIN:different+=1
        results["comparisons"].append(dict(pose=pose,hrtf_on_off_rms_delta=delta,
                state_distinct=delta>HRTF_DIFF_MIN))
    if (samples["on","left"].tobytes()==samples["on","right"].tobytes()
        or different<HRTF_MIN_POSES):
        results["status"]="FAIL"
    else:results["status"]="PASS_REAL_HRTF_ENABLED_PCM_DIFFERENTIATED"
    results["distinct_poses"]=different
    del results["actual_hrtf_states"]
    Path(out).write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
    print("OPENAL_HRTF_NUMERIC_BATCH",results["status"],"renders",len(results["cases"]),"different",different)
    if results["status"]=="FAIL":raise ValueError("predeclared HRTF difference falsified")
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: openal_hrtf_observe.py NATIVE_DIR OUT.json")
    observe(sys.argv[1],sys.argv[2])
