#!/usr/bin/env python3
"""Source-state-matched Blender 5.2 untouched groom vs 4.5 groom vs attached rigid hair.

The bare 5.2 observer does not add hair curves, UVs, skin weights, or shape-key
overrides. This research-only three-way oracle localizes the stage of mismatch,
not its final physical/biological cause. All source and release holds remain.
"""
import hashlib
import json
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pony_source_trajectory import classify,xyz
from pony_wind_state_interop import compare as compare_wind,weights,p95

SCHEMA="equine.pony.52_bare_wind_groom_48f.v1"
QUALITY="equine.pony.45_to_52_bare_and_curve_wind_diagnostic.v1"
SOURCE_KEYS={"schema","source_kind","source_blend_sha256","source_capsule_sha256","rig",
    "frame_count","source_surface","source_blender_version","wind_names","frames",
    "source_mutated_on_disk","in_memory_groom_geometry_modified","scientific_hold",
    "release_admission"}

def compare(skin,source45,bare52,rigid52):
    # Existing independent nine-channel, same-source 48f oracle is still
    # compulsory: its scientific RED does not turn this diagnostic green.
    prior=compare_wind(skin,source45,rigid52)
    gate=classify(skin)
    if type(bare52)!=dict or set(bare52)!=SOURCE_KEYS or bare52["schema"]!=SCHEMA:
        raise ValueError("unknown or incomplete 5.2 original bare-groom witness")
    if bare52["source_kind"]!="original_synthetic" or bare52["rig"]!="PonyRig30" or bare52["source_surface"]!="geometric_coat_mane_tail" or bare52["source_blender_version"]!="5.2.3" or bare52["frame_count"]!=48:
        raise ValueError("not actual original 5.2 bare groom")
    if bare52["source_blend_sha256"]!=skin["source_blend_sha256"] or bare52["source_capsule_sha256"]!=gate["source_capsule_sha256"]:
        raise ValueError("5.2 bare groom not same SHA-bound source")
    if bare52["source_mutated_on_disk"] is not False or bare52["in_memory_groom_geometry_modified"] is not False or bare52["scientific_hold"]!="KEEP" or bare52["release_admission"] is not False:
        raise ValueError("inappropriate source mutation or scientific admission")
    if type(bare52["frames"])!=list or len(bare52["frames"])!=48:
        raise ValueError("incomplete bare original frame sequence")
    cards={g["card_id"]:g for g in skin["guides"]}
    regions=("mane","forelock","tail")
    source_root={r:[] for r in regions}
    source_tip={r:[] for r in regions}
    curve_root={r:[] for r in regions}
    curve_tip={r:[] for r in regions}
    for fi,(a,b,c) in enumerate(zip(source45["frames"],bare52["frames"],rigid52["frames"])):
        if type(b)!=dict or set(b)!={"frame","wind_weights","guides"} or type(b["frame"])!=int or b["frame"]!=fi+1 or type(b["guides"])!=list or len(b["guides"])!=6:
            raise ValueError("5.2 bare frame missing/reordered")
        ww=weights(bare52["wind_names"],b["wind_weights"])
        wa=weights(source45["wind_names"],a["wind_weights"])
        wc=weights(rigid52["source_wind_key_names"],rigid52["source_wind_effective_weights_per_frame"][fi])
        if set(ww)!=set(wa) or set(ww)!=set(wc) or any(max(abs(ww[k]-wa[k]),abs(ww[k]-wc[k]))>1e-5 for k in ww):
            raise ValueError("nine wind sources not actually equivalent")
        if c.get("frame")!=fi+1 or type(c.get("guides"))!=list or len(c["guides"])!=6:
            raise ValueError("5.2 curve sample frame invalid")
        def index(items):
            if any(type(row)!=dict or type(row.get("card_id"))!=int for row in items):
                raise ValueError("invalid original source card identity")
            out={row["card_id"]:row for row in items}
            if len(out)!=6 or set(out)!=set(cards):raise ValueError("missing or duplicate original source card")
            return out
        original=index(a["guides"]);bare=index(b["guides"]);curve=index(c["guides"])
        for card,g in cards.items():
            reg=g["region"];o=original[card];v=bare[card];h=curve[card]
            if set(v)!={"card_id","region","root_m","tip_m"} or v["region"]!=reg or o["region"]!=reg or h["region"]!=reg:
                raise ValueError("bare source region or geometry fields false")
            root45,tip45=xyz(o["root_m"]),xyz(o["tip_m"])
            root52,tip52=xyz(v["root_m"]),xyz(v["tip_m"])
            rcurve,tcurve=xyz(h["actual_root_m"]),xyz(h["actual_tip_m"])
            claim=xyz(h["tip_minus_root_m"])
            if math.dist(tuple(tcurve[i]-rcurve[i] for i in range(3)),claim)>2e-6:
                raise ValueError("rigid 5.2 tip witness inconsistent")
            source_root[reg].append(math.dist(root45,root52))
            source_tip[reg].append(math.dist(tuple(tip45[i]-root45[i] for i in range(3)),
                tuple(tip52[i]-root52[i] for i in range(3))))
            curve_root[reg].append(math.dist(root52,rcurve))
            curve_tip[reg].append(math.dist(tuple(tip52[i]-root52[i] for i in range(3)),claim))
    def scores(xs):
        return {r:round(p95(xs[r]),8) for r in regions}
    source_p95=scores(source_tip)
    curve_p95=scores(curve_tip)
    source_root_max={r:round(max(source_root[r]),8) for r in regions}
    curve_root_max={r:round(max(curve_root[r]),8) for r in regions}
    excited=prior["max_wind_weight"]>.01
    if not excited:
        verdict="INCONCLUSIVE_WIND_NOT_EXCITED"
    elif max(source_p95.values())>.005 or max(source_root_max.values())>.005:
        verdict="UPSTREAM_52_BARE_SOURCE_GEOMETRY_DIFFERENT_SCIENCE_HOLD"
    elif max(curve_root_max.values())>.005:
        verdict="BOUNDARY_52_CURVE_ROOT_ATTACHMENT_DIFFERENT_SCIENCE_HOLD"
    elif max(curve_p95.values())>.005:
        verdict="SOURCE_GEOMETRY_EQUIVALENT_BUT_CURVE_TRANSFER_DIFFERS_SCIENCE_HOLD"
    else:
        verdict="SAMPLED_SOURCE_AND_CURVE_GEOMETRY_ALIGN_ENGINEERING_ONLY"
    return {"schema":QUALITY,"source_blend_sha256":skin["source_blend_sha256"],
        "source_capsule_sha256":gate["source_capsule_sha256"],"guides":6,"frames":48,
        "max_original45_to_bare52_root_error_m_by_region":source_root_max,
        "p95_original45_to_bare52_vector_error_m_by_region":source_p95,
        "max_bare52_to_curve52_root_error_m_by_region":curve_root_max,
        "p95_bare52_to_curve52_vector_error_m_by_region":curve_p95,
        "p95_original45_to_curve52_vector_error_m_by_region":prior["p95_tip_vector_45_vs_52_m_by_region"],
        "full_nine_wind_channels_same_value_per_frame":True,
        "observed_original_wind_activity":excited,"verdict":verdict,
        "source_mutated_on_disk":False,"native_blender_source_surface_pre_curve":True,
        "source_geometry_rest_only_no_dynamic_collision":True,
        "signed_body_penetration_qualified":False,"physical_hair_material_qualified":False,
        "visual_accepted":False,"scientific_hold":"KEEP","release_or_CPE_admission":False}

def native(args):
    import bpy
    if len(args)!=3:raise SystemExit("usage: --native original45.blend skin_capsule.json out.json")
    source,capsule_path,out=map(Path,args)
    if not source.is_file() or not capsule_path.is_file() or out.exists() or not 4096<source.stat().st_size<300000000:
        raise ValueError("original source absent, unbounded, or witness overwrite")
    skin=json.loads(capsule_path.read_text());gate=classify(skin)
    if bpy.app.version[:3]!=(5,2,3) or hashlib.sha256(source.read_bytes()).hexdigest()!=skin["source_blend_sha256"]:
        raise ValueError("source must be exact SHA and native Blender 5.2.3")
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
    rig=bpy.data.objects.get("PonyRig30")
    groom=bpy.data.objects.get("geometric_coat_mane_tail")
    if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=30 or groom is None or groom.type!="MESH" or len(groom.data.vertices)!=10500 or len(groom.data.polygons)!=8400:
        raise ValueError("bare original source rig/groom topology absent")
    if not any(m.type=="ARMATURE" and m.object==rig for m in groom.modifiers):
        raise ValueError("original bare groom skin binding absent")
    keys=[k for k in groom.data.shape_keys.key_blocks if k.name.startswith("wind_")] if groom.data.shape_keys else []
    if len(keys)!=9:raise ValueError("missing original nine wind keys")
    result={"schema":SCHEMA,"source_kind":"original_synthetic",
        "source_blend_sha256":skin["source_blend_sha256"],
        "source_capsule_sha256":gate["source_capsule_sha256"],"rig":"PonyRig30",
        "frame_count":48,"source_surface":"geometric_coat_mane_tail",
        "source_blender_version":"5.2.3","wind_names":[k.name for k in keys],
        "frames":[],"source_mutated_on_disk":False,"in_memory_groom_geometry_modified":False,
        "scientific_hold":"KEEP","release_admission":False}
    scene=bpy.context.scene
    scene.frame_set(0);scene.frame_set(1)
    for f in range(1,49):
        scene.frame_set(f);bpy.context.view_layer.update()
        w=[float(k.value) for k in keys]
        weights(result["wind_names"],w)
        ev=groom.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
        if mesh is None or len(mesh.vertices)!=10500:
            raise ValueError("native 5.2 bare original evaluated groom topology absent")
        try:
            mat=ev.matrix_world.copy();rows=[]
            for g in skin["guides"]:
                i=10*g["card_id"]
                root=mat@((mesh.vertices[i].co+mesh.vertices[i+1].co)*.5)
                tip=mat@((mesh.vertices[i+8].co+mesh.vertices[i+9].co)*.5)
                rows.append({"card_id":g["card_id"],"region":g["region"],
                    "root_m":[float(v) for v in root],"tip_m":[float(v) for v in tip]})
            result["frames"].append({"frame":f,"wind_weights":w,"guides":rows})
        finally:ev.to_mesh_clear()
    if hashlib.sha256(source.read_bytes()).hexdigest()!=skin["source_blend_sha256"]:
        raise ValueError("original source bytes changed while bare observing")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("ORIGINAL_52_BARE_NINE_WIND_KEYS_48F_NOT_RELEASE",json.dumps({
        "source_blend_sha256":result["source_blend_sha256"],"frames":48,"guides":6,
        "source_modified":False},sort_keys=True))

def main(argv):
    argv=argv[argv.index("--")+1:] if "--" in argv else argv
    if len(argv)==4 and argv[0]=="--native":return native(argv[1:])
    if len(argv)==5 and argv[0]=="--compare":
        source,source45,bare52,rigid52=[json.loads(Path(f).read_text()) for f in argv[1:]]
        result=compare(source,source45,bare52,rigid52)
        out=Path(argv[5]) if len(argv)>5 else None
        raise ValueError("use explicit 5-input compare including output path")
    if len(argv)==6 and argv[0]=="--compare":
        source,source45,bare52,rigid52=[json.loads(Path(f).read_text()) for f in argv[1:5]]
        out=Path(argv[5])
        if out.exists():raise ValueError("refuse witness overwrite")
        result=compare(source,source45,bare52,rigid52)
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        print("ORIGINAL_45_TO_52_BARE_TO_CURVE_STAGED_CAUSAL_WITNESS",json.dumps(result,sort_keys=True))
        return
    raise SystemExit("usage: --native original.blend skin.json output.json | --compare skin.json original45.json bare52.json curves52.json out.json")

if __name__=="__main__":main(sys.argv[1:])
