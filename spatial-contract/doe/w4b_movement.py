"""W4b original moving-block trajectory qualification; no sample-continuous claims.

A single original mono source is reused across all four geometry-only render plans.
Source and source-to-geometry manifests are sha256-bound to the W3c canonical DoE.
"""
import array
import hashlib
import json
import math
import struct
import sys
import wave
from pathlib import Path

from inspect_native_w3 import decode_float_pcm

RATE = 48000
BLOCK = 1024
CASES = 42
BLOCKS_PER_CASE = 12
FRAMES_PER_CASE = BLOCK * BLOCKS_PER_CASE
MODES = ("static", "yaw_left_75", "yaw_right_75", "range_2_to_20")
LAYOUTS = {"surround_5_1": 6, "surround_7_1": 8}
SOURCE_RIGHTS = "ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"
VLC_SHA = "d149ed9744fd399b835c6f2920511f8cbcfce5ea"
MOVING_THRESHOLD = 0.001
MIN_DISTINCT_CASES = 20
PREFIX_TOL = 1e-7

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def wrap(az):
    return ((az + 180.0) % 360.0) - 180.0

def pose(mode, az, elevation, block):
    if mode not in MODES or not 0 <= block < BLOCKS_PER_CASE:
        raise ValueError("invalid mode or block")
    az = float(az)
    distance = 10.0
    if mode == "yaw_left_75":
        az = wrap(az + (-75.0 if 3 <= block < 6 else 75.0 if block >= 6 else 0.0))
    if mode == "yaw_right_75":
        az = wrap(az + (75.0 if 3 <= block < 6 else -75.0 if block >= 6 else 0.0))
    if mode == "range_2_to_20":
        distance = 2.0 if 3 <= block < 6 else 20.0 if block >= 6 else 10.0
    return az, float(elevation), distance

def make_source(path):
    with Path(path).open("xb") as out:
        with wave.open(out, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            for case in range(CASES):
                samples = bytearray(FRAMES_PER_CASE * 2)
                for i in range(9 * BLOCK):
                    frame = case * FRAMES_PER_CASE + i
                    value = 0.12 * math.sin(2 * math.pi * 410 * frame / RATE)
                    if i in (3 * BLOCK, 6 * BLOCK):
                        value += 0.3
                    struct.pack_into("<h", samples, 2*i, int(round(value*32767)))
                wav.writeframesraw(samples)
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()) != (1,2,RATE,CASES*FRAMES_PER_CASE):
            raise ValueError("invalid original source")

def prepare(root):
    root = Path(root)
    first = json.loads((root/"source_manifest.json").read_text())
    doe_file = root/"original_doe.json"
    doe = json.loads(doe_file.read_text())
    if (first["classification"] != SOURCE_RIGHTS or first["rate"] != RATE
        or first["channels"] != 1 or first["upstream_videolan"] != VLC_SHA
        or doe["schema"] != "spatial_audio.offaxis_doe.v1"
        or len(doe["cases"]) != CASES or sha(doe_file) != first["doe_sha256"]
        or sha(root/"w3c_cases.tsv") != first["case_table_sha256"]
        or sha(root/"original_410hz.wav") != first["source_wav_sha256"]):
        raise ValueError("W3 source geometry or pinned rights changed")
    source = root/"w4b_motion.wav"
    make_source(source)
    plans = {}
    for mode in MODES:
        plan = root/("w4b_"+mode+".tsv")
        with plan.open("x") as f:
            for i,case in enumerate(doe["cases"]):
                for j in range(BLOCKS_PER_CASE):
                    az,el,distance=pose(mode,case["relative_azimuth_deg"],case["elevation_deg"],j)
                    start=(i*BLOCKS_PER_CASE+j)*BLOCK
                    f.write(f"{start}\t{BLOCK}\t{az:.9f}\t{el:.9f}\t{distance:.9f}\n")
        plans[mode] = sha(plan)
    manifest = dict(schema="spatial_audio/w4b_motion_batch/1",
        rights=SOURCE_RIGHTS,
        source_sha256=sha(source),
        case_count=CASES, blocks_per_case=BLOCKS_PER_CASE,
        frames_per_case=FRAMES_PER_CASE, rate=RATE,
        original_doe_sha256=first["doe_sha256"],
        provider_sha=VLC_SHA, plans_sha256=plans,
        modes=list(MODES), layouts=LAYOUTS,
        moving_threshold=MOVING_THRESHOLD,
        minimum_distinct_cases=MIN_DISTINCT_CASES,
        prefix_tolerance=PREFIX_TOL,
        source_spec="410HZ_TONE_9_BLOCKS_2_SWITCH_TRANSIENTS_PLUS_3_ZERO_BLOCKS",
        direct_stereo="NAN_QUARANTINED")
    (root/"w4b_manifest.json").write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n")
    print("W4B_SOURCE_BATCH_READY",json.dumps(manifest,sort_keys=True))

def stage_profile(pcm, channels, case, stage):
    first = (case*FRAMES_PER_CASE+(stage*3+1)*BLOCK)*channels
    end = (case*FRAMES_PER_CASE+(stage*3+3)*BLOCK)*channels
    if not first < end <= len(pcm):
        raise ValueError("invalid stage bounds")
    power=[0.0]*channels
    for pos in range(first,end):
        power[pos%channels]+=pcm[pos]*pcm[pos]
    if power[3]>1e-9:
        raise ValueError("LFE energy in a source-only fixture")
    total=sum(v for idx,v in enumerate(power) if idx!=3)
    if total < 1e-10:
        raise ValueError("nonzero source segment silent")
    return [math.sqrt(v/total) if j!=3 else 0.0 for j,v in enumerate(power)]

def read_cases(blob, channels):
    pcm=decode_float_pcm(blob,channels,CASES*FRAMES_PER_CASE)
    profiles=[]
    for case in range(CASES):
        profiles.append([stage_profile(pcm,channels,case,stage) for stage in range(3)])
    return pcm,profiles

def observe(root, output):
    root=Path(root)
    manifest=json.loads((root/"w4b_manifest.json").read_text())
    if (manifest["schema"]!="spatial_audio/w4b_motion_batch/1" or manifest["rights"]!=SOURCE_RIGHTS
        or manifest["provider_sha"]!=VLC_SHA or manifest["case_count"]!=CASES
        or manifest["layouts"]!=LAYOUTS or manifest["modes"]!=list(MODES)
        or manifest["moving_threshold"]!=MOVING_THRESHOLD
        or manifest["minimum_distinct_cases"]!=MIN_DISTINCT_CASES
        or manifest["prefix_tolerance"]!=PREFIX_TOL
        or sha(root/"w4b_motion.wav")!=manifest["source_sha256"]
        or sha(root/"original_doe.json")!=manifest["original_doe_sha256"]):
        raise ValueError("W4b original source or preregistered thresholds changed")
    for mode in MODES:
        if sha(root/("w4b_"+mode+".tsv"))!=manifest["plans_sha256"][mode]:
            raise ValueError("motion plan mutated")
    results=dict(schema="spatial_audio/w4b_native_motion_observer/1",
                 manifest=manifest, results=[], comparisons=[], failures=[],
                 unqualified=["SAMPLE_CONTINUOUS_MOTION","HRTF","ROOM_REFLECTIONS",
                              "HUMAN_AUDITION","DOPPLER","SOURCE_POSITION_VELOCITY"])
    for layout,n in LAYOUTS.items():
        rec={}
        for mode in MODES:
            path=root/("w4b_"+mode+"_"+layout+".wav")
            blob=path.read_bytes()
            pcm,profiles=read_cases(blob,n)
            rec[mode]=(pcm,profiles)
            # All complete native buffers checked by strict WAV parser.
            results["results"].append(dict(layout=layout,mode=mode,
                pcm_sha256=hashlib.sha256(blob).hexdigest(),cases=len(profiles),
                zero_source_tail_energy=sum(float(pcm[i]*pcm[i]) for case in range(CASES)
                    for i in range((case*FRAMES_PER_CASE+9*BLOCK)*n,
                                   ((case+1)*FRAMES_PER_CASE)*n))))
        static_pcm,static_profiles=rec["static"]
        for mode in ("yaw_left_75","yaw_right_75","range_2_to_20"):
            pcm,profiles=rec[mode]
            # First case before changing the azimuth is an independent exact-input control.
            prefix=3*BLOCK*n
            maximum=max(abs(static_pcm[i]-pcm[i]) for i in range(prefix))
            if maximum>PREFIX_TOL:
                results["failures"].append(dict(layout=layout,mode=mode,reason="initial_prefix_not_equal",max_delta=maximum))
            different=0
            deltas=[]
            for case in range(CASES):
                delta=max(abs(profiles[case][stage][ch]-static_profiles[case][stage][ch])
                          for stage in (1,2) for ch in range(n) if ch!=3)
                deltas.append(delta)
                if delta>MOVING_THRESHOLD:
                    different+=1
            results["comparisons"].append(dict(layout=layout,mode=mode,
                distinct_cases=different,total_cases=CASES,
                max_normalized_channel_delta=max(deltas),
                min_normalized_channel_delta=min(deltas),
                first_case_prefix_max_abs_error=maximum,
                criterion="OBSERVATIONAL_DISTANCE_ONLY" if mode=="range_2_to_20" else "AT_LEAST_20_CASES_CHANGE"))
            if mode.startswith("yaw_") and different<MIN_DISTINCT_CASES:
                results["failures"].append(dict(layout=layout,mode=mode,reason="moving_source_unobservable",count=different))
    results["status"]="PASS" if len(results["results"])==8 and len(results["comparisons"])==6 and not results["failures"] else "FAIL"
    Path(output).write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
    print("W4B_NATIVE_MOTION_BATCH",results["status"],"renders",len(results["results"]),
          "comparisons",len(results["comparisons"]),"failures",len(results["failures"]))
    if results["status"]!="PASS":
        raise ValueError("native W4b movement falsified; inspect retained numeric receipt")

def main():
    if len(sys.argv)==3 and sys.argv[1]=="prepare":
        prepare(sys.argv[2])
    elif len(sys.argv)==4 and sys.argv[1]=="observe":
        observe(sys.argv[2],sys.argv[3])
    else:
        raise SystemExit("w4b_movement.py prepare DIR | observe DIR OUTPUT_JSON")
if __name__=="__main__":
    main()
