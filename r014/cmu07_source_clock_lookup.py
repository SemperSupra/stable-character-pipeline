"""Source-neutral exact-rational capture clock adaptor for held CMU07_01 walk.

This emits ONLY frame-index interpolation metadata, no joints, capture, weights
or reconstructed gait. Reuse W07 typed walk_motion -> walk_retarget contracts,
not a competing motion IR. Capture rights and native skeleton gates are external.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from fractions import Fraction
from pathlib import Path

SOURCE_FRAMES=316
SOURCE_RATE=120
SOURCE_LOOP_START=55
SOURCE_LOOP_END=186
SOURCE_TRIAL="CMU subject 07 trial 07_01 (private R009 source intake)"
VALID_PROVENANCE={"UNKNOWN","ESTIMATED","OBSERVED"}

def bounded_fraction(s):
    try:
        f=Fraction(str(s))
    except (ValueError,ZeroDivisionError) as e:
        raise ValueError("invalid rational capture timing") from e
    if f<=0 or f>480:
        raise ValueError("capture timing out of bounds")
    return f

def clock_table(out_rate,frames,cadence,source_sha=None,contact="UNKNOWN"):
    if not isinstance(out_rate,int) or not 1<=out_rate<=120:
        raise ValueError("invalid target fps")
    if not isinstance(frames,int) or not 2<=frames<=3600:
        raise ValueError("invalid target frame count")
    if contact not in VALID_PROVENANCE or contact!="UNKNOWN":
        raise ValueError("source contact cannot be claimed from timing metadata")
    if source_sha is not None and (len(source_sha)!=64 or
        any(c not in "0123456789abcdef" for c in source_sha)):
        raise ValueError("invalid source pin")
    cadence=bounded_fraction(cadence)
    # R009 source-specific loop choice recorded in protected DLE, not
    # independently verified as a seamless lower-body cycle.
    span=SOURCE_LOOP_END-SOURCE_LOOP_START+1
    rows=[]
    seams=[]
    for n in range(frames):
        phase=(Fraction(n,out_rate)*cadence)%1
        p=phase*span
        lo=p.numerator//p.denominator
        alpha=p-lo
        j0=SOURCE_LOOP_START+lo
        j1=SOURCE_LOOP_START+(lo+1)%span
        assert SOURCE_LOOP_START<=j0<=SOURCE_LOOP_END
        assert SOURCE_LOOP_START<=j1<=SOURCE_LOOP_END
        if j1==SOURCE_LOOP_START and alpha!=0:
            seams.append(n+1)
        rows.append({
          "target_frame_1based":n+1,
          "source_a_frame_1based":j0,
          "source_b_frame_1based":j1,
          "source_b_weight_num":alpha.numerator,
          "source_b_weight_den":alpha.denominator,
          "target_time_s_num":n,
          "target_time_s_den":out_rate,
          "contact_state":"UNKNOWN",
          "support_authority":"NOT_DERIVED_FROM_CLOCK",
          "source_motion_admitted":False
        })
    return {
       "schema":"r014.cmu_capture_clock_lookup.research_only.v1",
       "status":"CLOCK_ONLY_WITH_REAL_CMUSOURCE_HASH_REQUIRED_TO_ENABLE_POSE_RETARGET",
       "source_trial":SOURCE_TRIAL,
       "source_frames":SOURCE_FRAMES,
       "capture_rate_hz":SOURCE_RATE,
       "source_loop_window_1based":[SOURCE_LOOP_START,SOURCE_LOOP_END],
       "source_capture_artifact_sha256":source_sha,
       "capture_artifact_opened":False,
       "source_cadence_hz":str(cadence),
       "output_rate_hz":out_rate,
       "output_frames":frames,
       "source_loop_seam_interpolation_frames":seams,
       "source_time_fraction":"exact rational source sampling, no dropped/lost source indices",
       "limitations":[
          "Real CMU ASF/AMC privately ingested by R009, but NO capture available/processed by this public job",
          "No source joint rotations/positions/contacts; no fake OBSERVED foot phases",
          "Source loop window R009 experimental; pose or velocity continuity at seam NOT verified",
          "No source calibrated world-unit, hand/toe tracking quality, anatomical JCS or MHR binding",
          "Use W07 typed motion IR for data; this JSON is *only* an independent clock lookup",
          "No single-source gait naturalness or product/film approval"
       ],
       "lookup":rows
    }

def selftest():
    x=clock_table(24,169,"1/2")
    assert len(x["lookup"])==169
    assert x["lookup"][0]["source_a_frame_1based"]==SOURCE_LOOP_START
    assert x["lookup"][48]["source_a_frame_1based"]==SOURCE_LOOP_START
    assert x["lookup"][96]["source_a_frame_1based"]==SOURCE_LOOP_START
    assert x["lookup"][144]["source_a_frame_1based"]==SOURCE_LOOP_START
    assert all(z["contact_state"]=="UNKNOWN" and not z["source_motion_admitted"] for z in x["lookup"])
    # target 24fps, cadence 0.5Hz, each frame advances 2.75 source frames.
    assert x["lookup"][1]["source_a_frame_1based"]==57
    assert x["lookup"][1]["source_b_weight_num"]==3
    assert x["lookup"][1]["source_b_weight_den"]==4
    assert x["lookup"][1]["source_b_frame_1based"]==58
    for fps in (24,30,60):
        y=clock_table(fps,169,"1/2")
        assert all(SOURCE_LOOP_START<=r["source_a_frame_1based"]<=SOURCE_LOOP_END for r in y["lookup"])
    for args in ((0,169,"1/2"),(24,0,"1/2"),(24,169,0),(24,169,"NaN")):
        try:clock_table(*args)
        except ValueError:pass
        else:raise AssertionError("bad source clock accepted")
    for contact in ("OBSERVED","ESTIMATED","forged"):
        try:clock_table(24,169,"1/2",contact=contact)
        except ValueError:pass
        else:raise AssertionError("fake contact accepted")
    try:clock_table(24,169,"1/2",source_sha="wrong")
    except ValueError:pass
    else:raise AssertionError("bad pin accepted")
    print("R014_CMU_CLOCK_METADATA_GATES_PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path)
    p.add_argument("--fps",type=int,default=24)
    p.add_argument("--frames",type=int,default=169)
    p.add_argument("--cadence",default="1/2")
    p.add_argument("--source-sha")
    a=p.parse_args()
    selftest()
    if a.out:
        x=clock_table(a.fps,a.frames,a.cadence,a.source_sha)
        a.out.parent.mkdir(parents=True,exist_ok=True)
        data=(json.dumps(x,indent=2,sort_keys=True)+"\n").encode()
        a.out.write_bytes(data)
        print("R014_CLOCK_LOOKUP",json.dumps({
          "frames":len(x["lookup"]),"sha256":hashlib.sha256(data).hexdigest(),
          "seams":x["source_loop_seam_interpolation_frames"],
          "status":x["status"]},sort_keys=True))

if __name__=="__main__":main()
