"""Independent source kinematics oracle parity, public aggregate evidence only.

The Go solver does NOT use the upstream Python parse/rotation equations;
this comparator computes the pinned MIT AMCParser Python reference on raw,
SHA-matched original CMU files, then compares all joints at ALL frames.
GO/Python complete trajectories must remain disposable runner temp only.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

source = Path(__file__).resolve().parents[1] / "source_admission"
sys.path.insert(0, str(source))
from cmu07_original_metadata import assess, SCALE_TO_METERS

EXPECTED={
    "asf":"c29414591d76a34885bff0b04a2666bf9659f869751a2549591c55277cf95b04",
    "07_01":"3ca8e8b834481c97c32e9dd555f8c9023e33b6c52d93c9d556c83570204bf3f2",
    "07_02":"a6062c6c6bce037241d345ca8d802ab36a5cf003b60f759aa7b1db545219c065",
}
ROLES={
    "pelvis_source_root":"root",
    "left_femur_parent":"lhipjoint","left_femur":"lfemur",
    "left_tibia":"ltibia","left_ankle_segment":"lfoot","left_toe_segment":"ltoes",
    "right_femur_parent":"rhipjoint","right_femur":"rfemur",
    "right_tibia":"rtibia","right_ankle_segment":"rfoot","right_toe_segment":"rtoes",
}
def finite_joints(positions):
    a=np.asarray(positions,dtype=np.float64)
    assert a.shape[-1]==3 and np.isfinite(a).all()
    return a
def compare(a,b):
    if set(a)!=set(b):
        raise ValueError("joint name set mismatch, missing or forged bone")
    names=sorted(a)
    x=finite_joints([a[n] for n in names])
    y=finite_joints([b[n] for n in names])
    err=np.linalg.norm(x-y,axis=1)
    return names,float(np.max(err)),float(np.sqrt(np.mean(err*err))),names[int(np.argmax(err))]
def selftest():
    original={"root":[0,0,0],"foot":[1,0,0]}
    _,maxerr,_,_=compare(original,original)
    assert maxerr==0
    for bad in ({"root":[0,0,0]},
                {"root":[0,0,0],"foot":[-1,0,0]},
                {"root":[0,0,float("nan")],"foot":[1,0,0]},
                {"root":[0,0,0],"foot":[1,0]}):
        try:
            _,x,_,_=compare(original,bad)
            if x>1e-7:raise ValueError("independent FK mismatch")
        except (ValueError,AssertionError): pass
        else: raise AssertionError("forgeable/invalid source-oracle comparison")
    print("CMU07_INDEPENDENT_FK_PARITY_NEGATIVE_SELFTEST_PASS")
def main(args):
    verified=assess(args.asf,args.amc,args.motion)
    assert verified["source_files"]["asf"]["sha256"]==EXPECTED["asf"]
    assert verified["source_files"]["amc"]["sha256"]==EXPECTED[args.motion]
    raw=json.loads(args.go_ephemeral.read_text())
    assert raw["schema"]=="motion.cmu07.goindependent_fk_ephemeral.v1"
    assert raw["motion"]==args.motion and raw["clock_hz"]==120
    assert raw["source_sha256"]=={"asf":EXPECTED["asf"],"amc":EXPECTED[args.motion]}
    assert raw["bone_count"]==31
    assert len(raw["frames"])==verified["amc"]["original_measured_frames"]

    sys.path.insert(0,str(args.parser))
    from amc_parser import parse_asf,parse_amc
    nodes=parse_asf(str(args.asf))
    amc=parse_amc(str(args.amc))
    assert len(amc)==len(raw["frames"])
    assert len(nodes)==31
    assert set(ROLES.values()).issubset(nodes)
    global_max=0.
    sqerr=[]
    worst={}
    contact_candidates={r:[] for r in ("l","r")}
    velocities={r:[] for r in ("l","r")}
    root_world=[]
    for i,(channels,other) in enumerate(zip(amc,raw["frames"])):
        nodes["root"].set_motion(channels)
        native={}
        for name,b in nodes.items():
            native[name]=(np.asarray(b.coordinate,dtype=np.float64).reshape(3)*SCALE_TO_METERS).tolist()
        names,maxerr,rms,jname=compare(native,other)
        if maxerr>global_max:
            global_max=maxerr
            worst={"frame":i+1,"bone":jname}
        sqerr.append(rms*rms)
        root_world.append(native["root"])
        for r in ("l","r"):
            if i==0:continue
            b=np.asarray(native[r+"toes"])
            # Frame 1 is reconstructed from prior verified source bytes,
            # NOT an asserted measured foot sole/force-contact label.
            old=np.asarray(prev[r+"toes"])
            speed=float(np.linalg.norm(b-old)*120.0)
            velocities[r].append(speed)
        prev=native

    maxgate=1e-7  # in SOURCE WORLD metres, genuinely stringent cross-engine parity
    passed=bool(global_max<=maxgate)
    root=np.asarray(root_world)
    root_distance=float(np.linalg.norm(root[-1]-root[0]))
    known=verified["amc"]["converted_root_end_to_end_displacement_m_if_source_units_as_published"]
    if abs(root_distance-known)>1e-9:raise ValueError("independent original root endpoint mismatch")
    speeds={}
    for r,x in velocities.items():
        arr=np.asarray(x,dtype=np.float64)
        speeds[r]={"p05_m_s":float(np.quantile(arr,.05)),
                   "p50_m_s":float(np.quantile(arr,.5)),
                   "p95_m_s":float(np.quantile(arr,.95)),
                   "max_m_s":float(arr.max())}
    receipt={
        "schema":"motion.cmu07.two_engine_original_fk_parity.v1",
        "source_motion":args.motion,
        "status":"PASS_DUAL_ENGINE_3D_FK_GEOMETRY_ONLY" if passed else "HOLD_FK_PARITY_DISAGREEMENT",
        "original_source_sha256":{"asf":EXPECTED["asf"],"amc":EXPECTED[args.motion]},
        "original_source_120hz_frames":len(amc),
        "original_source_original_bone_count":31,
        "original_source_channel_nodes":len(verified["amc"]["joint_channels"]),
        "reference_engine":"MIT CalciferZh AMCParser pinned commit 08e5a3662e197e7e40eed2c18fc254282eb381f9, numpy/transforms3d",
        "independent_engine":"Go 1.23 stdlib manually parsed source ASF/AMC, own RzRyRx Euler and hierarchy",
        "all_frames_all_bones_compared":len(amc)*len(nodes),
        "source_m_units":"original CMU published (1/0.45)*2.54/100 factor; not physically independently calibrated",
        "max_world_position_disagreement_m":global_max,
        "rms_world_position_disagreement_m":math.sqrt(sum(sqerr)/len(sqerr)),
        "worst_case":worst,"independent_tolerance_m":maxgate,
        "original_root_end_to_end_m":root_distance,
        "left_and_right_toe_speed_stats_UNOBSERVED_CONTACT":speeds,
        "source_role_proposal_NOT_NATIVE_TARGET_MAPPING":ROLES,
        "source_motion_ir":"reuse W07 source-neutral contract in public walking #84; no parallel new authority",
        "source_contact_status":"UNKNOWN; kinematics only, not observed ground pressure",
        "source_physical_anatomy_status":"UNKNOWN; native FK names do not certify target MHR/MPFB anatomical counterparts",
        "capture_bytes_or_full_trajectories_in_artifact":False,
        "owner_admission":"R012 source venue/rights and R014 target material remain separate and NOT production-admitted",
        "not_admitted":["No full native MHR or MPFB retarget",
                        "No toe/sole/heel force plate or measured stance",
                        "No independent true coordinate metre calibration",
                        "No cinematic video, hair, skin or full anatomy",
                        "No private R009 identities or protected datasets"]}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/(args.motion+".two_engine_fk_parity.json")).write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("CMU07_SOURCE_DUAL_ENGINE_FK",json.dumps({
        "motion":args.motion,"frames":len(amc),"positions_compared":len(amc)*len(nodes),
        "max_err_m":global_max,"rms_err_m":receipt["rms_world_position_disagreement_m"],
        "status":receipt["status"]},sort_keys=True),flush=True)
    if not passed:raise SystemExit(4)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--selftest",action="store_true")
    ap.add_argument("--motion",choices=("07_01","07_02"))
    ap.add_argument("--asf",type=Path)
    ap.add_argument("--amc",type=Path)
    ap.add_argument("--parser",type=Path)
    ap.add_argument("--go-ephemeral",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    if a.selftest:selftest()
    else:
        if any(x is None for x in (a.motion,a.asf,a.amc,a.parser,a.go_ephemeral,a.out)):
            ap.error("six source arguments required")
        main(a)
