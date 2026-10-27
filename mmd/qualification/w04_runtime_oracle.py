#!/usr/bin/env python3
"""W04 third genuine Babylon MmdRuntime vs prior independent converter oracle.

Source units and 3 frames only. Explicitly NOT native MikuMikuDance CCD or
global pose/physics equivalence. Works on actual source-bound raw JSON receipts.
"""
import argparse, copy, hashlib, json, math
from pathlib import Path

ORIGINAL_PMX="fadfc3cb3d365cdb4b0c4cc26652c2e831a02ec7da518caae9142dd711468583"
ORIGINAL_VMD="e61ae2953c6cd34904fec2c59ae95fe64ed043ce0cde93e1c3d5db3d12ed149c"
ORIGINAL_G9_PMX="311e8da1c17d924ac40ed84a543a162c79b5ad7a19d5718a62072f8908757d42"
ORIGINAL_G9_VMD="b69a57beeffe067cf7a100cb45ac83259c05004ffda5c599da54b5fb5b60b663"

def validate(runtime, direct, tracks):
    if runtime.get("status")!="PASS_BABYLON_MMD_ACTUAL_BOUND_RUNTIME_SELECTED_FRAMES_ONLY":
        raise ValueError("runtime source not actually evaluated")
    if direct.get("schema")!="scp.mmd.ik.contact.v1" or direct.get("status")!="PASS_IK_TARGET_TRACKING" or not direct.get("gate_pass"):
        raise ValueError("independent converter source receipt did not pass its own gate")
    if tracks.get("status")!="PASS_GENUINE_NULLENGINE_AND_BABYLON_MMD_VMD_ANIMATION_OBJECTS":
        raise ValueError("source loader track audit missing")
    cases={c["case"]:c for c in runtime["cases"]}
    if set(cases)!={"g9","g10"}:raise ValueError("missing runtime source experiment")
    if cases["g10"]["model_sha256"]!=ORIGINAL_PMX or cases["g10"]["motion_sha256"]!=ORIGINAL_VMD:
        raise ValueError("G10 model-motion source digest mismatch")
    if cases["g9"]["model_sha256"]!=ORIGINAL_G9_PMX or cases["g9"]["motion_sha256"]!=ORIGINAL_G9_VMD:
        raise ValueError("G9 model-motion source digest mismatch")
    if not all(c["actual_runtime_model"] and c["actual_bound_animation"] for c in cases.values()):
        raise ValueError("runtime was not actually attached")
    report=[]
    snaps=cases["g10"]["snapshots"]
    if [s["frame"] for s in snaps]!=[0,15,30]:raise ValueError("G10 observed source sample time drift")
    for row in snaps:
        frame=row["frame"]
        bones={b["name"]:b["world_xyz"] for b in row["bones"]}
        if not {"足首","足ＩＫ"}.issubset(bones):raise ValueError("source-native leg bone identity lost")
        ankle,goal=bones["足首"],bones["足ＩＫ"]
        if len(ankle)!=3 or len(goal)!=3 or not all(math.isfinite(x) for x in ankle+goal):
            raise ValueError("invalid bone position")
        delta=math.dist(ankle,goal)
        direct_row=direct["ik_enabled"].get(str(frame))
        if direct_row is None:raise ValueError("prior independent converter did not measure this frame")
        earlier=float(direct_row["error"])
        # Before this independent test: 0.002 original PMX/source-unit tolerance
        # calibrated below G10b acceptance of .05; NOT a physical-meter metric.
        if not math.isfinite(earlier) or not 0<=delta<.05 or abs(delta-earlier)>.002:
            raise ValueError(f"independent MMD pose target deviation exceeds two-engine acceptance at frame {frame}")
        report.append({"frame":frame,"babylon_goal_error_source_unit":delta,
                       "independent_converter_error_source_unit":earlier,
                       "absolute_delta_source_unit":abs(delta-earlier),
                       "accepted_pairwise_tolerance_source_unit":.002})
    morph=cases["g9"]["snapshots"]
    if [s["frame"] for s in morph]!=[0,15,30]:raise ValueError("morph frame origin mismatch")
    native_tracks={c["kind"]:c for c in tracks["cases"]}
    if native_tracks["g9"]["source_vmd_sha256"]!=ORIGINAL_G9_VMD:raise ValueError("original morph keyframes source mismatch")
    upstream={t["name"]:dict(zip(t["frames"],t["weights"])) for t in native_tracks["g9"]["morph_tracks"]}
    if set(upstream)!={"まばたき","笑い"}:raise ValueError("lost Japanese source morph names")
    for sample in morph:
        for name in upstream:
            observed=sample["morphWeights"][name]
            expected=upstream[name][sample["frame"]]
            if not math.isfinite(observed) or abs(observed-expected)>.002:
                raise ValueError("actual bound morph deviates from source VMD at a sampled frame")
    return {"status":"PASS_INDEPENDENT_DIRECT_VS_REAL_BABYLON_G10_SELECTED_IK_AND_G9_MORPH",
      "frame_errors":report,
      "morph_observations":morph,
      "source_classes":["original author-created PMX+VMD","actual Babylon NullEngine MmdRuntime",
                        "previous independently executed MIT mmd2gltf G10b reader"],
      "claims_not_qualified":["native MikuMikuDance CCD solver equality","complete 31-frame/world skin parity",
         "friction/physics/ground support","independent viewer video rendering","physical meter scale"]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--runtime",type=Path,required=True)
    ap.add_argument("--direct",type=Path,required=True)
    ap.add_argument("--tracks",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    r=json.loads(a.runtime.read_bytes());d=json.loads(a.direct.read_bytes());t=json.loads(a.tracks.read_bytes())
    result=validate(r,d,t)
    # Real receipt-derived adversarial mutations: sham source, wrong pose,
    # and forged morph response must each get a red result.
    for case,mut in (
       ("wrong_pmx",lambda x:x["cases"][0].update(model_sha256="0"*64)),
       ("wrong_ankle",lambda x:next(c for c in x["cases"] if c["case"]=="g10")["snapshots"][1]["bones"][2]["world_xyz"].__setitem__(0,55)),
       ("frozen_blink",lambda x:next(c for c in x["cases"] if c["case"]=="g9")["snapshots"][1]["morphWeights"].__setitem__("まばたき",0)),
    ):
        cloned=copy.deepcopy(r);mut(cloned)
        try:validate(cloned,d,t)
        except (ValueError,KeyError,TypeError):pass
        else:raise AssertionError(f"malicious candidate admitted: {case}")
    result["red_controls"]=["wrong_pmx","wrong_ankle","frozen_blink"]
    result["source_receipt_sha256"]={
      "runtime":hashlib.sha256(a.runtime.read_bytes()).hexdigest(),
      "direct":hashlib.sha256(a.direct.read_bytes()).hexdigest(),
      "tracks":hashlib.sha256(a.tracks.read_bytes()).hexdigest()}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("W04_TRUE_THIRD_ENGINE_COMPARE",json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
