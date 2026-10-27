#!/usr/bin/env python3
"""W04 31-frame genuine Babylon MmdRuntime vs previously generated independent
MIT mmd2gltf GLB. Reuses untouched G10b evaluated glTF accessor/math functions.
No human model, no fake solver, no native MMD CCD, no physical scale claims.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

EXPECTED_PMXS = {
    "g10": ("fadfc3cb3d365cdb4b0c4cc26652c2e831a02ec7da518caae9142dd711468583",
             "e61ae2953c6cd34904fec2c59ae95fe64ed043ce0cde93e1c3d5db3d12ed149c"),
    "g9": ("311e8da1c17d924ac40ed84a543a162c79b5ad7a19d5718a62072f8908757d42",
            "b69a57beeffe067cf7a100cb45ac83259c05004ffda5c599da54b5fb5b60b663")
}
FRAME_IDS=list(range(31))
DIST_TOL=.002
MAX_GOAL_ERROR=.05

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def glb_31(glb, prior, source):
    if sha(glb)!=prior["source_ik_glb_sha256"]:
        raise ValueError("GLB does not match prior independently qualified source")
    scene,raw=source.load(glb)
    nodes=scene.get("nodes",[])
    original_names=("腰","ひざ","足首","足ＩＫ")
    ids={name:next((i for i,n in enumerate(nodes) if n.get("name")==name),None) for name in original_names}
    if None in ids.values() or len(set(ids.values()))!=4:
        raise ValueError("nonunique original Japanese bone names")
    parent={}
    for i,node in enumerate(nodes):
        for child in node.get("children",[]):
            if child in parent:raise ValueError("DAG ambiguous parent")
            parent[child]=i
    if parent.get(ids["ひざ"])!=ids["腰"] or parent.get(ids["足首"])!=ids["ひざ"]:
        raise ValueError("wrong original rig hierarchy")
    tracks={}
    times=None
    if len(scene["animations"])!=1:raise ValueError("ambiguous direct converter animation")
    for ch in scene["animations"][0]["channels"]:
        k=(ch["target"]["node"],ch["target"]["path"])
        if k in tracks:raise ValueError("duplicate glTF motion tracks")
        sampler=scene["animations"][0]["samplers"][ch["sampler"]]
        ts=[v[0] for v in source.get_accessor(scene,raw,sampler["input"])]
        samples=source.get_accessor(scene,raw,sampler["output"])
        if len(ts)!=31 or len(samples)!=31 or any(abs(t-i/30)>1e-3 for i,t in enumerate(ts)):
            raise ValueError("original converter missing 31 actual 30fps samples")
        if times is not None and ts!=times:raise ValueError("source converters do not share timeline")
        times=ts
        tracks[k]=samples
    def world(i,frame,seen=frozenset()):
        if i in seen:raise ValueError("cyclic animated joint graph")
        node=nodes[i]
        pos=tracks.get((i,"translation"))
        ori=tracks.get((i,"rotation"))
        local_pos=pos[frame] if pos else node.get("translation",(0.,0.,0.))
        local_rot=ori[frame] if ori else node.get("rotation",(0.,0.,0.,1.))
        if i not in parent:return tuple(local_pos),tuple(local_rot)
        p,q=world(parent[i],frame,seen|{i})
        v=source.rotate(q,local_pos)
        return tuple(p[d]+v[d] for d in range(3)),source.quat_mul(q,local_rot)
    return [
      {"frame":i,
       "ankle":world(ids["足首"],i)[0],
       "goal":world(ids["足ＩＫ"],i)[0]}
      for i in FRAME_IDS
    ]

def verify(runtime, glb_records):
    if runtime.get("status")!="PASS_BABYLON_MMD_ACTUAL_BOUND_RUNTIME_31_FRAMES_ONLY":
        raise ValueError("31-frame real engine claim missing")
    cases={c["case"]:c for c in runtime["cases"]}
    if set(cases)!=set(EXPECTED_PMXS) or len(runtime["cases"])!=2:
        raise ValueError("real source cases absent/duplicated")
    for kind,(pmx,vmd) in EXPECTED_PMXS.items():
        row=cases[kind]
        if row["model_sha256"]!=pmx or row["motion_sha256"]!=vmd:
            raise ValueError("original PMX/VMD SHA altered")
        if not row.get("actual_runtime_model") or not row.get("actual_bound_animation"):
            raise ValueError("not an evaluated real MMD model")
        if [x["frame"] for x in row["snapshots"]]!=FRAME_IDS:
            raise ValueError("31-frame timeline missing/duplicated")
    out=[]
    goal_errors=[]
    for b,d in zip(cases["g10"]["snapshots"],glb_records):
        frame=b["frame"]
        assert frame==d["frame"]
        names=[x["name"] for x in b["bones"]]
        if len(names)!=len(set(names)) or set(names)!={"腰","ひざ","足首","足ＩＫ"}:
            raise ValueError("actual MmdRuntime Japanese bones missing/duplicated")
        bmap={x["name"]:x["world_xyz"] for x in b["bones"]}
        ankle,goal=bmap["足首"],bmap["足ＩＫ"]
        if not all(len(v)==3 and all(math.isfinite(x) for x in v) for v in (ankle,goal,d["ankle"],d["goal"])):
            raise ValueError("nonfinite or non-3D joint position")
        e=math.dist(ankle,goal)
        ref=math.dist(d["ankle"],d["goal"])
        delta=abs(e-ref)
        if e>=MAX_GOAL_ERROR or ref>=MAX_GOAL_ERROR or delta>=DIST_TOL:
            raise ValueError(f"first independent source-unit target-error failure at {frame}: b={e},d={ref},delta={delta}")
        goal_errors.append((e,ref))
        out.append({"frame":frame,"babylon_source_unit":e,"direct_converter_source_unit":ref,
                   "absolute_delta_source_unit":delta})
    if math.dist(cases["g10"]["snapshots"][0]["bones"][-1]["world_xyz"],
                 cases["g10"]["snapshots"][-1]["bones"][-1]["world_xyz"])<=.35:
        raise ValueError("moving source IK controller stopped")
    morph=cases["g9"]["snapshots"]
    originals={"まばたき":{0:0.,15:1.,30:0.},"笑い":{0:0.,15:.35,30:1.}}
    for name,keys in originals.items():
        values=[]
        for x in morph:
            if set(x["morphWeights"])!=set(originals):raise ValueError("morph missing or renamed")
            v=x["morphWeights"][name]
            if not math.isfinite(v) or v<-.001 or v>1.001:raise ValueError("invalid interpolated G9 morph")
            if x["frame"] in keys and abs(v-keys[x["frame"]])>.002:
                raise ValueError("native real G9 morph diverges from source keyed VMD")
            values.append(v)
        if len(set(round(v,4) for v in values))<8:
            raise ValueError("intermediate morph source motion frozen or stepped")
        if max(abs(a-b) for a,b in zip(values,values[1:]))>.25:
            raise ValueError("unphysical numerical discontinuity in native morph frame sampling")
    return {"status":"PASS_REAL_BABYLON_VS_DIRECT_G10_31_FRAME_GOAL_ERROR_AND_G9_INTERMEDIATE_MORPHS",
      "schema":"scp.mmd.w04-31frame-cross-engine.v1",
      "source_scale":"PMX_SOURCE_UNIT; METERS_PER_UNIT_UNKNOWN",
      "source_frames":FRAME_IDS,
      "g10":out,
      "max_pairwise_delta":max(x["absolute_delta_source_unit"] for x in out),
      "max_babylon_goal_error":max(x[0] for x in goal_errors),
      "max_direct_goal_error":max(x[1] for x in goal_errors),
      "g9_weights":[{"frame":r["frame"],"weights":r["morphWeights"]} for r in morph],
      "gates":{"max_goal_error_source_unit":MAX_GOAL_ERROR,
               "max_pairwise_goal_error_delta_source_unit":DIST_TOL,
               "intermediate_unique_round_4":8,
               "max_adjacent_morph_weight_step":.25},
      "not_qualified":["full world-joint pose equivalence (only goal-error magnitude)",
                        "Blender 31-frame equivalence","native MikuMikuDance CCD equivalence",
                        "ground contact or physics","actual browser pixels","physical meters"]}

def main():
    ap=argparse.ArgumentParser()
    for name in ("runtime","direct-glb","prior","original-glb-verifier","out"):
        ap.add_argument("--"+name,type=Path,required=True)
    a=ap.parse_args()
    prior=json.loads(a.prior.read_text())
    if prior.get("status")!="PASS_IK_TARGET_TRACKING" or not prior.get("gate_pass"):
        raise ValueError("prior G10b independent converter proof not accepted")
    spec=importlib.util.spec_from_file_location("original_g10b_read_only",a.original_glb_verifier)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    direct=glb_31(a.direct_glb,prior,module)
    runtime=json.loads(a.runtime.read_text())
    report=verify(runtime,direct)
    # First-failure/suppression adversaries (no success from sparse frames).
    mutants=[
      ("duplicate_midframe",lambda r:r["cases"][0]["snapshots"][7].update(frame=6)),
      ("goal_error_midframe",lambda r:next(c for c in r["cases"] if c["case"]=="g10")["snapshots"][7]["bones"][2]["world_xyz"].__setitem__(0,12.)),
      ("g9_freeze_intermediate",lambda r:next(c for c in r["cases"] if c["case"]=="g9")["snapshots"][7]["morphWeights"].__setitem__("まばたき",.8)),
      ("wrong_g10_vmd_sha",lambda r:next(c for c in r["cases"] if c["case"]=="g10").update(motion_sha256="0"*64))
    ]
    # For "g9_freeze_intermediate" mutate every between-key point into a plateau.
    red=[]
    for name,mut in mutants:
        clone=copy.deepcopy(runtime)
        if name=="g9_freeze_intermediate":
            for row in next(c for c in clone["cases"] if c["case"]=="g9")["snapshots"][1:15]:
                row["morphWeights"]["まばたき"]=.8
        else:mut(clone)
        try:verify(clone,direct)
        except (ValueError, KeyError, AssertionError,TypeError):red.append(name)
        else:raise AssertionError("negative control passed: "+name)
    report["negative_rejections"]=red
    report["input_sha256"]={"babylon_31_runtime":sha(a.runtime),"direct_G10_GLb":sha(a.direct_glb),
                            "prior_G10b_receipt":sha(a.prior),"original_G10b_verifier_source":sha(a.original_glb_verifier)}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("W04_31_FRAMES_VERIFIED",json.dumps({k:v for k,v in report.items() if k not in ("g10","g9_weights")},sort_keys=True),flush=True)
if __name__=="__main__":main()
