#!/usr/bin/env python3
"""Three-audience R009 wardrobe console: inspect, export, Blender command plan.

No network, private asset, dynamic plugin or hidden state. The v1 slot/preset
contract is authoritative; this is a thin source-verified UX/DX layer.
"""
import argparse
import hashlib
import json
from pathlib import Path
from modular_wardrobe_v1 import ACTORS,PRESETS
from wardrobe_portable_export_v2 import export

SCHEMA="scp.r009.original_wardrobe_console.v2"
SWITCH=Path(__file__).with_name("wardrobe_switch_blender.py")
OPTIONAL_PRESET_SLOTS=frozenset({"accessory"})

def resolve_actor_presets(manifest):
    """Explicitly omit optional missing actor slots; reject required omissions."""
    slots_by_actor=manifest.get("actor_slots")
    if not isinstance(slots_by_actor,dict) or set(slots_by_actor)!=set(ACTORS):
        raise ValueError("ACTOR_SLOT_SET_DRIFT")
    known=set().union(*(set(s) for s in PRESETS.values()))
    resolved={}
    for actor in ACTORS:
        slots=slots_by_actor[actor]
        if not isinstance(slots,dict) or set(slots)-known:
            raise ValueError("UNKNOWN_ACTOR_SLOT:"+actor)
        per_preset={}
        for preset,requested in PRESETS.items():
            requested=set(requested)
            absent=requested-set(slots)
            required_absent=absent-OPTIONAL_PRESET_SLOTS
            if required_absent:
                raise ValueError("REQUIRED_PRESET_SLOT_MISSING:"+actor+":"+preset+":"+','.join(sorted(required_absent)))
            per_preset[preset]={
                "active":sorted(requested&set(slots)),
                "omitted_optional":sorted(absent),
            }
        resolved[actor]=per_preset
    return resolved

def inspect(manifest,source=None):
    m=json.loads(Path(manifest).read_text())
    if m.get("schema")!="scp.original_wardrobe_manifest.v1":
        raise ValueError("UNKNOWN_WARDROBE_MANIFEST")
    if set(m.get("subjects",[]))!=set(ACTORS):
        raise ValueError("UNEXPECTED_ACTORS")
    if m.get("presets")!={k:list(v) for k,v in PRESETS.items()}:
        raise ValueError("PRESET_CONTRACT_DRIFT")
    if source:
        value=hashlib.sha256(Path(source).read_bytes()).hexdigest()
        if value!=m.get("derived_sha256"):
            raise ValueError("SOURCE_MANIFEST_SHA_MISMATCH")
    return {"schema":SCHEMA,"subjects":list(ACTORS),
            "presets":{k:list(v) for k,v in PRESETS.items()},
            "actor_slots":{a:sorted(m["actor_slots"][a]) for a in ACTORS},
            "resolved_actor_presets":resolve_actor_presets(m),
            "optional_slot_semantics":"EXPLICIT_OMIT_IF_MISSING",
            "source_sha256":m["derived_sha256"],
            "independent_alt_cuts":bool(m.get("separate_new_geometry_for_alternate",False)),
            "human_appearance_accepted":False,"release_approved":False}

def plan_blender(source,out,receipt,preset,actor,blender="blender"):
    if preset not in PRESETS:raise ValueError("UNKNOWN_PRESET")
    if actor!="all" and actor not in ACTORS:raise ValueError("UNKNOWN_ACTOR")
    src,dest,rcpt=map(lambda s:Path(s).resolve(),(source,out,receipt))
    if len({src,dest,rcpt})!=3:
        raise ValueError("SOURCE_OVERWRITE_REFUSED")
    if not src.is_file():raise ValueError("SAVED_INPUT_BLEND_REQUIRED")
    if not SWITCH.is_file():raise ValueError("WARDROBE_BLENDER_SCRIPT_MISSING")
    return {"schema":SCHEMA,"operation":"blender_non_destructive_derive",
        "argv":[blender,"-b",str(src),"--python-exit-code","8",
                "--python",str(SWITCH),"--","--preset",preset,"--actor",actor,
                "--out",str(dest),"--receipt",str(rcpt)],
        "source_blend_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
        "source_unchanged_required":True,"human_appearance_accepted":False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    cmd=parser.add_subparsers(dest="command",required=True)
    info=cmd.add_parser("inspect",help="Inspect source-bound slots and presets")
    info.add_argument("--manifest",required=True)
    info.add_argument("--input",help="Optionally verify exact source GLB hash")
    info.add_argument("--human",action="store_true",
                      help="Print human-readable preset summary rather than JSON")
    out=cmd.add_parser("export",help="Non-destructive portable GLB preset derivation")
    out.add_argument("--input",required=True)
    out.add_argument("--manifest",required=True)
    out.add_argument("--out",required=True)
    out.add_argument("--receipt",required=True)
    out.add_argument("--aster",choices=sorted(PRESETS),default="signature")
    out.add_argument("--juniper",choices=sorted(PRESETS),default="signature")
    plan=cmd.add_parser("plan-blender",help="Return argv for offline editable Blender variant")
    plan.add_argument("--source",required=True)
    plan.add_argument("--out",required=True)
    plan.add_argument("--receipt",required=True)
    plan.add_argument("--preset",choices=sorted(PRESETS),required=True)
    plan.add_argument("--actor",choices=("all",)+ACTORS,default="all")
    plan.add_argument("--blender",default="blender")
    a=parser.parse_args(argv)
    if a.command=="inspect":
        result=inspect(a.manifest,a.input)
        if a.human:
            print("R009 original wardrobe | fictional adults | research only")
            for name,slots in result["presets"].items():
                print(name+": "+", ".join(slots))
            print("Distinct alternate cuts: "+("yes" if result["independent_alt_cuts"] else "no"))
            for actor,choices in result["resolved_actor_presets"].items():
                for preset,slots in choices.items():
                    if slots["omitted_optional"]:
                        print(actor+" "+preset+" omitted optional: "+", ".join(slots["omitted_optional"]))
            print("Human/cloth acceptance: NOT QUALIFIED")
            return result
    elif a.command=="export":
        inspect(a.manifest,a.input)
        result=export(a.input,a.manifest,a.out,a.receipt,
                      {ACTORS[0]:a.aster,ACTORS[1]:a.juniper})
    else:
        result=plan_blender(a.source,a.out,a.receipt,a.preset,a.actor,a.blender)
    print(json.dumps(result,sort_keys=True))
    return result

if __name__=="__main__":
    try:main()
    except (ValueError,FileNotFoundError,KeyError) as e:
        print(json.dumps({"schema":SCHEMA,"ok":False,
            "error":str(e),"human_appearance_accepted":False}),flush=True)
        raise SystemExit(2)
