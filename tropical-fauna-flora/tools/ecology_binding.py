#!/usr/bin/env python3
"""E0 -> rendered scene binding. Illustrative behavior, not ecology calibration or contact IK."""
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = "scp.ecology.scene-binding.v1"

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def verify(report, mapping, glb_sha):
    if report.get("schema") != "scp.ecology.v1":
        raise ValueError("unsupported ecology report")
    frames = report.get("frames")
    if not isinstance(frames, list) or not 1 <= len(frames) <= 600:
        raise ValueError("missing ecology frames")
    ledger = report.get("ledger", {})
    if (ledger.get("balanced") is not True or
        ledger.get("initial_g", -1) + ledger.get("regrowth_g", -1) -
        ledger.get("consumed_g", -1) != ledger.get("final_g")):
        raise ValueError("unbalanced ecology ledger")
    if any(not isinstance(ledger.get(key), int) or ledger[key] < 0 for key in
           ("initial_g", "regrowth_g", "consumed_g", "final_g")):
        raise ValueError("invalid mass ledger")
    canonical = {"frames": frames, "ledger": ledger}
    if report.get("digest_sha256") != hashlib.sha256(json.dumps(canonical, separators=(",", ":")).encode()).hexdigest():
        raise ValueError("tampered ecology report digest")
    if mapping.get("schema") != "scp.ecology.scene-map.v1" or mapping.get("model_sha256") != glb_sha:
        raise ValueError("mapping does not match GLB identity")
    patch_names = set(mapping.get("patch_positions", {}))
    actor_names = set(mapping.get("actor_nodes", {}))
    first = frames[0]
    if patch_names != set(p["id"] for p in first["patches"]):
        raise ValueError("unmapped vegetation patch")
    if actor_names != set(a["id"] for a in first["animals"]):
        raise ValueError("unmapped fauna actor")
    nodes = [x.get("node") for x in mapping["actor_nodes"].values()]
    if len(nodes) != len(set(nodes)) or any(not isinstance(n,str) or not n.startswith("fauna/") or not n.endswith("/root") for n in nodes):
        raise ValueError("ambiguous actor root node")
    for position in list(mapping["patch_positions"].values()) + [a["origin"] for a in mapping["actor_nodes"].values()]:
        if (not isinstance(position, list) or len(position) != 3 or any(
            isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or abs(x)>100 for x in position)):
            raise ValueError("bad position")
    for i, state in enumerate(frames, start=1):
        if state["tick"] != i:
            raise ValueError("nonsequential ecology tick")
        if set(p["id"] for p in state["patches"]) != patch_names or set(a["id"] for a in state["animals"]) != actor_names:
            raise ValueError("unstable ecology entity universe")
        for patch in state["patches"]:
            if not 0 <= patch["biomass_g"] <= patch["capacity_g"] or patch["capacity_g"] <= 0:
                raise ValueError("out-of-bounds forage")
        for animal in state["animals"]:
            if animal["patch"] not in patch_names or animal["kind"] != mapping["actor_nodes"][animal["id"]]["kind"]:
                raise ValueError("unmapped animal type or target")

def compile_binding(report, mapping, glb_sha, count=48, fps=12):
    verify(report, mapping, glb_sha)
    if not 12 <= count <= 120 or not 8 <= fps <= 30:
        raise ValueError("unbounded CPU video workload")
    current = {name: [float(v) for v in meta["origin"]] for name, meta in mapping["actor_nodes"].items()}
    images=[]
    for index in range(count):
        state=report["frames"][min(len(report["frames"])-1, index*len(report["frames"])//count)]
        actors=[]
        for animal in sorted(state["animals"], key=lambda a:a["id"]):
            name=animal["id"]
            target=mapping["patch_positions"][animal["patch"]]
            adjustment=.55 if animal["kind"]=="egret" else 0.
            dx,dy=target[0]-current[name][0],target[1]+adjustment-current[name][1]
            distance=math.hypot(dx,dy)
            if distance:
                step=min(2.0/fps,distance)/distance
                current[name][0]=round(current[name][0]+dx*step,6)
                current[name][1]=round(current[name][1]+dy*step,6)
            base=mapping["actor_nodes"][name]["origin"]
            actors.append({"id":name,"node":mapping["actor_nodes"][name]["node"],
                "patch":animal["patch"],"offset":[round(current[name][i]-base[i],6) for i in range(3)]})
        patches=[{"id":p["id"],"position":mapping["patch_positions"][p["id"]],
                  "biomass_g":p["biomass_g"],"capacity_g":p["capacity_g"],
                  "ratio":round(p["biomass_g"]/p["capacity_g"],6)}
                 for p in sorted(state["patches"],key=lambda p:p["id"])]
        images.append({"frame":index+1,"ecology_tick":state["tick"],"actors":actors,"patches":patches})
    result={"schema":SCHEMA,"frames":images,"frame_count":count,"fps":fps,
            "source_report_sha256":report["digest_sha256"],"model_sha256":glb_sha,
            "fidelity":report["fidelity"],
            "disclaimer":"ILLUSTRATIVE guidance and biomass markers; not gait, physics, calibrated ecology or true plant growth"}
    result["binding_sha256"]=digest(result)
    return result

def main():
    parser=argparse.ArgumentParser()
    for name in ("report","map","model","out"):
        parser.add_argument("--"+name,required=True)
    parser.add_argument("--frames",type=int,default=48)
    parser.add_argument("--fps",type=int,default=12)
    args=parser.parse_args()
    model=Path(args.model).read_bytes()
    if len(model)>100*1024*1024:
        parser.error("oversized GLB")
    result=compile_binding(json.loads(Path(args.report).read_text()),
                           json.loads(Path(args.map).read_text()),
                           hashlib.sha256(model).hexdigest(),args.frames,args.fps)
    target=Path(args.out)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("ECOLOGY_BINDING_OK",result["binding_sha256"])

if __name__=="__main__":
    main()
