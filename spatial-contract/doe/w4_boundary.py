"""W3c W4a: byte-pinned original impulse onset perturbation, not an acoustic oracle."""
import array
import hashlib
import json
import struct
import sys
import wave
from pathlib import Path

from inspect_native_w3 import decode_float_pcm

RATE, BLOCK, CASE_BLOCKS, CASES = 48000, 1024, 47, 42
CASE_FRAMES = BLOCK * CASE_BLOCKS
OFFSETS = (0, 1, 255, 256, 1023, 1024, 1025)
THRESHOLD = 1e-6
LIMIT = 1
RIGHTS = "ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"
VLC_SHA = "d149ed9744fd399b835c6f2920511f8cbcfce5ea"
GAIN_ONLY_REFERENCE = "EBU_STATIC_GAINS_NOT_TIME_DOMAIN_ORACLE"
LAYOUTS = {"surround_5_1": 6, "surround_7_1": 8}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def offset_for_case(index):
    if not 0 <= index < CASES:
        raise ValueError("invalid case")
    return OFFSETS[index % len(OFFSETS)]

def shift_error(a, b, injected):
    if not all(isinstance(x, int) for x in (a,b,injected)):
        raise ValueError("noninteger timing")
    return (b-a)-injected

def create_wav(path, shifted):
    with Path(path).open("xb") as output:
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            for case in range(CASES):
                frame = offset_for_case(case) if shifted else 0
                payload = bytearray(2*CASE_FRAMES)
                struct.pack_into("<h", payload, frame*2, int(round(0.45*32767)))
                wav.writeframesraw(payload)
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()) != (1, 2, RATE, CASES*CASE_FRAMES):
            raise ValueError("bad original input WAV")

def prepare(root):
    root = Path(root)
    first = json.loads((root/"source_manifest.json").read_text())
    doe_path = root/"original_doe.json"
    doe = json.loads(doe_path.read_text())
    if (first["classification"] != RIGHTS or first["rate"] != RATE or first["channels"] != 1
        or first["blocks_per_case"] != CASE_BLOCKS or first["frames"] != CASES*CASE_FRAMES
        or first["upstream_videolan"] != VLC_SHA or doe["schema"] != "spatial_audio.offaxis_doe.v1"
        or len(doe["cases"]) != CASES or sha(doe_path) != first["doe_sha256"]
        or sha(root/"w3c_cases.tsv") != first["case_table_sha256"]
        or sha(root/"original_410hz.wav") != first["source_wav_sha256"]):
        raise ValueError("prior original source, ENU or provenance drift")
    sources = {}
    for kind in ("baseline", "shifted"):
        path = root/("w4_"+kind+".wav")
        create_wav(path, shifted=kind=="shifted")
        sources[kind] = sha(path)
    manifest = dict(schema="spatial_audio/w4a_impulse_boundary/1", rights=RIGHTS, rate=RATE,
                    case_count=CASES, frames_per_case=CASE_FRAMES,
                    original_doe_sha256=first["doe_sha256"],
                    original_plan_sha256=sha(root/"w3c_videolan_blocks.tsv"),
                    native_provider_sha=VLC_SHA, sources_sha256=sources,
                    offsets=list(OFFSETS), input_impulse_amplitude_pcm16=int(round(0.45*32767)),
                    detector_threshold=THRESHOLD, max_timing_shift_error_samples=LIMIT,
                    ebu_time_domain_oracle=GAIN_ONLY_REFERENCE,
                    direct_stereo="NAN_QUARANTINED")
    (root/"w4_sources.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("W4A_SOURCE_PREPARE_PASS",json.dumps(manifest,sort_keys=True))

def onset_and_tail(pcm, channel_count, case_index):
    beg = case_index*CASE_FRAMES*channel_count
    end = beg+CASE_FRAMES*channel_count
    sub = pcm[beg:end]
    onset = None
    last = None
    energy = 0.0
    tail_energy = 0.0
    lfe_energy = 0.0
    peak = 0.0
    # Decode *all* case samples; source source-onset and late-window statistics are independent.
    for frame in range(CASE_FRAMES):
        start = frame*channel_count
        event = False
        for ch in range(channel_count):
            sample = sub[start+ch]
            peak = max(peak, abs(sample))
            if ch == 3:
                lfe_energy += sample*sample
                continue
            sq = sample*sample
            energy += sq
            if frame >= CASE_FRAMES-1024:
                tail_energy += sq
            if abs(sample)>THRESHOLD:
                event = True
        if event:
            if onset is None:
                onset = frame
            last = frame
    if onset is None or peak < THRESHOLD or peak > 1.0 or lfe_energy > 1e-9:
        raise ValueError("silent, clipped or LFE-leaking case")
    return dict(onset_frame=onset, last_detected_frame=last, peak=peak,
                lfe_energy=lfe_energy, total_energy=energy,
                late_1024_energy_fraction=tail_energy/energy,
                last_detected_relative_to_onset=last-onset)

def verify_source(root, manifest):
    for kind in ("baseline","shifted"):
        if sha(root/("w4_"+kind+".wav")) != manifest["sources_sha256"][kind]:
            raise ValueError("original source hash mismatch")
    if sha(root/"original_doe.json") != manifest["original_doe_sha256"] or sha(root/"w3c_videolan_blocks.tsv") != manifest["original_plan_sha256"]:
        raise ValueError("Go plan not equal to preparer")
    if (manifest["schema"] != "spatial_audio/w4a_impulse_boundary/1"
        or manifest["rights"] != RIGHTS or manifest["offsets"] != list(OFFSETS)
        or manifest["detector_threshold"] != THRESHOLD
        or manifest["max_timing_shift_error_samples"] != LIMIT
        or manifest["native_provider_sha"] != VLC_SHA
        or manifest["ebu_time_domain_oracle"] != GAIN_ONLY_REFERENCE):
        raise ValueError("prospective contract drift")

def observe(root, output):
    root=Path(root)
    manifest=json.loads((root/"w4_sources.json").read_text())
    verify_source(root,manifest)
    result=dict(schema="spatial_audio/w4a_numeric_observer/1", source_manifest=manifest,
                acceptance="ABS_ONSET_SHIFT_ERROR_LE_1_SAMPLE_ONLY", cases=[], failed_cases=[],
                scope_not_tested=["HRTF", "room_reverb", "sample_continuous_motion",
                                  "device_latency", "human_audition", "EBU_waveform_parity"])
    for layout,n in LAYOUTS.items():
        observed={}
        for kind in ("baseline","shifted"):
            path=root/("w4_"+kind+"_"+layout+".wav")
            pcm=decode_float_pcm(path.read_bytes(),n,CASES*CASE_FRAMES)
            observed[kind]=[onset_and_tail(pcm,n,i) for i in range(CASES)]
        for i in range(CASES):
            a,b=observed["baseline"][i],observed["shifted"][i]
            offset=offset_for_case(i)
            error=shift_error(a["onset_frame"],b["onset_frame"],offset)
            entry=dict(case=i,layout=layout,source_shift_frames=offset,
                       baseline=a,shifted=b,observed_shift_error_frames=error,
                       status="PASS" if abs(error)<=LIMIT else "FAIL")
            result["cases"].append(entry)
            if entry["status"]=="FAIL":
                result["failed_cases"].append(dict(case=i,layout=layout,error=error))
    result["status"]="PASS" if len(result["cases"])==84 and not result["failed_cases"] else "FAIL"
    Path(output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("W4A_NUMERIC_RECEIPT",result["status"],"pairs",len(result["cases"]),
          "failures",len(result["failed_cases"]))
    if result["status"]!="PASS":
        raise ValueError("frozen relative impulse timing falsified: see numeric receipt")

def main():
    if len(sys.argv)==3 and sys.argv[1]=="prepare":
        prepare(sys.argv[2])
    elif len(sys.argv)==4 and sys.argv[1]=="observe":
        observe(sys.argv[2],sys.argv[3])
    else:
        raise SystemExit("usage: w4_boundary.py prepare DIR | observe DIR OUT.json")
if __name__=="__main__":
    main()
