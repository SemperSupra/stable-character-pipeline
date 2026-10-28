"""Independent W3c W3 PCM temporal/spectral falsification monitor.

EBU object gains are an angular reference, NOT a waveform, phase, room or
audibility reference. All source SHA/case labels/channel sequences checked.
The predeclared 0.005 applies ONLY to normalized steady-state tone gains.
Transient onset, phase and filter tails are measurements, not parity claims.
"""
import array
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

LAYOUTS = {
    "surround_5_1": ["M+030","M-030","M+000","LFE1","M+110","M-110"],
    "surround_7_1": ["M+030","M-030","M+000","LFE1","M+090","M-090","M+135","M-135"]
}
KINDS = {"sine_410":410,"sine_930":930,"impulse_burst":None}
GAIN_LIMIT = .005
BLOCK = 1024
CASE_BLOCKS = 47

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_custody(ebu,video):
    a=json.loads((ebu/"w3_source_variants.json").read_text())
    b=json.loads((video/"w3_source_variants.json").read_text())
    if a != b or a["schema"] != "spatial_audio/w3c_w3_source_variants/1" or a["rights"] != "ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC":
        raise ValueError("two native runner source/provenance mismatch")
    if a["case_count"] != 42 or a["blocks_per_case"] != CASE_BLOCKS or a["sample_rate_hz"] != 48000 or a["channels"] != 1 or a["frames"] != 42*CASE_BLOCKS*BLOCK:
        raise ValueError("unqualified source clock")
    if set(a["variant_source_wav_sha256"])!=set(KINDS) or a["direct_stereo"] != "NAN_QUARANTINED":
        raise ValueError("missing original source variant or stereo quarantine")
    for root in (ebu,video):
        if sha(root/"original_doe.json") != a["doe_sha256"] or sha(root/"w3c_cases.tsv") != a["case_table_sha256"]:
            raise ValueError("geometry/CASE table drift")
        for kind,digest in a["variant_source_wav_sha256"].items():
            path = root / ("original_410hz.wav" if kind=="sine_410" else kind+".wav")
            if sha(path)!=digest:
                raise ValueError("source WAV hash drift "+kind)
    doe=json.loads((ebu/"original_doe.json").read_text())
    if doe["schema"]!="spatial_audio.offaxis_doe.v1" or len(doe["cases"])!=42:
        raise ValueError("noncanonical source DoE")
    return a,doe

def ebu_reference(path, cases):
    rows={}
    case_by_id={c["id"]:c for c in cases}
    if len(case_by_id)!=42:raise ValueError("duplicate geometry source IDs")
    for line in path.read_text().splitlines():
        p=line.split("\t")
        if len(p)!=7:raise ValueError("bad EBU native row")
        ident,layout,az,el,yaw,da,di=p
        if ident not in case_by_id or layout not in LAYOUTS or (ident,layout) in rows:
            raise ValueError("EBU unknown/duplicate ID or layout")
        source=case_by_id[ident]
        if (abs(float(az)-source["relative_azimuth_deg"])>1e-6 or
            abs(float(el)-source["elevation_deg"])>1e-6 or
            abs(float(yaw)-source["listener_yaw_deg"])>1e-6):
            raise ValueError("source/EBU ENU yaw mismatch")
        direct=[float(x) for x in da.split(",")]
        diffuse=[float(x) for x in di.split(",")]
        if (len(direct)!=len(LAYOUTS[layout]) or len(diffuse)!=len(direct)
            or not all(math.isfinite(v) for v in direct+diffuse)
            or abs(direct[3])>1e-6 or abs(diffuse[3])>1e-6):
            raise ValueError("EBU finite/layout/LFE reference mismatch")
        rows[(ident,layout)]=direct
    if len(rows)!=84:raise ValueError("EBU cases incomplete")
    return rows

def decode_float_pcm(blob, n, count):
    # Strict original renderer 44-byte IEEE float32 RIFF, no implicit channels.
    if (blob[:4]!=b"RIFF" or blob[8:16]!=b"WAVEfmt "
        or blob[36:40]!=b"data" or len(blob)!=44+count*n*4
        or struct.unpack_from("<I",blob,4)[0]!=len(blob)-8
        or struct.unpack_from("<I",blob,16)[0]!=16
        or struct.unpack_from("<HHIIHH",blob,20)!=(3,n,48000,48000*n*4,n*4,32)
        or struct.unpack_from("<I",blob,40)[0]!=count*n*4):
        raise ValueError("truncated/swap/trailing/native WAV header")
    if sys.byteorder!="little":raise ValueError("host float endianness unsupported")
    output=array.array("f")
    output.frombytes(blob[44:])
    if len(output)!=count*n or not all(math.isfinite(x) and abs(x)<=1 for x in output):
        raise ValueError("NaN/Inf/clipping in full decoded native PCM")
    return output

def phase(v,frequency,global_start):
    # Measured complex fundamental of the last 1024 PCM samples, not an EBU phase.
    re=im=0.0
    for k,x in enumerate(v):
        angle=2*math.pi*frequency*(global_start+k)/48000
        re+=x*math.cos(angle)
        im-=x*math.sin(angle)
    return math.atan2(im,re)

def normalized_error(rms,ebu):
    if not rms or len(rms)!=len(ebu):raise ValueError("wrong speaker count")
    a=math.sqrt(sum(x*x for j,x in enumerate(rms) if j!=3))
    b=math.sqrt(sum(x*x for j,x in enumerate(ebu) if j!=3))
    if a<1e-8 or b<1e-8:raise ValueError("no comparable tone energy")
    return max(abs(rms[j]/a-ebu[j]/b) for j in range(len(rms)) if j!=3)

def measure_case(pcm, n, idx, source_gain, frequency):
    start=idx*CASE_BLOCKS*BLOCK*n
    end=start+CASE_BLOCKS*BLOCK*n
    values=pcm[start:end]
    if len(values)!=CASE_BLOCKS*BLOCK*n:raise ValueError("case PCM truncated")
    channel_energy=[0.0]*n
    first=[0.0]*n
    late=[0.0]*n
    peak=0.0
    # FULL case-frame readback, not only an RMS on the last window.
    for j,x in enumerate(values):
        ch=j%n
        sq=x*x
        channel_energy[ch]+=sq
        if j<BLOCK*n:first[ch]+=sq
        if j>=(CASE_BLOCKS-1)*BLOCK*n:late[ch]+=sq
        if abs(x)>peak:peak=abs(x)
    if channel_energy[3]>1e-9:raise ValueError("native LFE leakage")
    if peak<1e-8:raise ValueError("native case silent")
    rms=[math.sqrt(e/BLOCK) for e in late]
    metrics={
        "peak":peak,
        "first_1024_energy":first,
        "last_1024_energy":late,
        "whole_case_energy":channel_energy,
        "late_1024_rms":rms,
        "source_input_kind":"steady_tone" if frequency else "impulse_burst"
    }
    if frequency:
        metrics["normalized_gain_max_error_vs_ebu"]=normalized_error(rms,source_gain)
        phases=[]
        for ch in range(n):
            if rms[ch] >= max(rms)*.05 and ch!=3:
                seq=[values[j*n+ch] for j in range((CASE_BLOCKS-1)*BLOCK,CASE_BLOCKS*BLOCK)]
                phases.append({"channel":LAYOUTS["surround_5_1" if n==6 else "surround_7_1"][ch],
                               "measured_input_relative_phase_rad":phase(seq,frequency,idx*CASE_BLOCKS*BLOCK+(CASE_BLOCKS-1)*BLOCK)})
        metrics["last_block_measured_phase_not_ebu_parity"]=phases
        metrics["phase_or_waveform_equivalence"]="UNSUPPORTED_NO_INDEPENDENT_EBU_WAVEFORM"
    else:
        # Time resolution is one 48k input sample, rendered onset depends on FIR.
        # Input burst is at the first sample of each independent case interval.
        onset=None
        for frame in range(CASE_BLOCKS*BLOCK):
            if any(abs(values[frame*n+ch])>1e-6 for ch in range(n) if ch!=3):
                onset=frame
                break
        if onset is None:raise ValueError("no detected transient")
        metrics["first_detected_native_transient_frame_1e_minus_6"]=onset
        metrics["tail_energy_fraction_last_1024"]=sum(late)/sum(channel_energy)
        metrics["waveform_ebu_comparison"]="UNSUPPORTED_EBU_ONLY_STATIC_GAIN"
    return metrics

def main():
    if len(sys.argv)!=4:raise SystemExit("usage: inspect_native_w3.py EBU_DIR VIDEO_DIR OUT.json")
    ebu=Path(sys.argv[1]);video=Path(sys.argv[2]);out=Path(sys.argv[3])
    m,doe=verify_custody(ebu,video)
    reference=ebu_reference(ebu/"ebu_native_84.tsv",doe["cases"])
    results=[]
    all_ok=True
    for kind,freq in KINDS.items():
        for layout,labels in LAYOUTS.items():
            name="w3_"+kind+"_"+layout+".wav"
            path=video/name
            blob=path.read_bytes()
            pcm=decode_float_pcm(blob,len(labels),m["frames"])
            for i,c in enumerate(doe["cases"]):
                measurements=measure_case(pcm,len(labels),i,reference[(c["id"],layout)],freq)
                max_err=measurements.get("normalized_gain_max_error_vs_ebu")
                status="PASS_VALID_TRANSIENT_ACQUISITION_NOT_WAVEFORM_PARITY"
                if freq:
                    status="PASS_TONE_SPEAKER_GAIN" if max_err<=GAIN_LIMIT else "FAIL_SPECTRAL_ANGULAR_GAIN"
                if status.startswith("FAIL"):all_ok=False
                results.append({
                    "case_id":c["id"],"layout":layout,
                    "speaker_labels":labels,"source_variant":kind,
                    "source_wav_sha256":m["variant_source_wav_sha256"][kind],
                    "native_pcm_sha256":sha(path),
                    "ebu_reference":"STATIC_OBJECT_DIRECT_ONLY",
                    "status":status,"metrics":measurements
                })
    summary={
        "schema":"spatial_audio/w3c_w3_spectral_transient/1",
        "status":"PASS_ALL_PREDECLARED_TONE_GAIN_AND_TRANSIENT_ACQUISITION" if all_ok else "FAIL_NATIVE_SPECTRAL_GAIN_FALSIFICATION",
        "rights":m["rights"],"case_count":42,
        "source_variants":m["variant_source_wav_sha256"],
        "source_doe_sha256":m["doe_sha256"],
        "native_engine_pins":{"ebu":m["upstream_libear"],"videolan":m["upstream_videolan"]},
        "observations_expected":42*2*3,"observations_count":len(results),
        "predeclared_steady_tone_gain_limit":GAIN_LIMIT,
        "input_sample_clock_hz":48000,
        "transient_phase_broadband_ebu_waveform_parity":"NOT_APPLICABLE_STATIC_GAIN_ONLY",
        "device_spatial_localization":"NOT_TESTED",
        "native_direct_stereo":"NAN_QUARANTINED",
        "cases":results
    }
    if len(results)!=summary["observations_expected"]:raise ValueError("missing cases")
    with out.open("x") as f:json.dump(summary,f,sort_keys=True,indent=2);f.write("\n")
    print("W3_NATIVE_SPECTRAL_TRANSIENT_OBSERVATION",json.dumps({k:v for k,v in summary.items() if k!="cases"},sort_keys=True))
    if not all_ok:raise SystemExit("W3 numerical falsification: source spectrum changed comparable normalized speaker gains")

if __name__=="__main__":
    main()
