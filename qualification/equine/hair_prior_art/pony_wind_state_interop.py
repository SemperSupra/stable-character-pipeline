#!/usr/bin/env python3
"""Reversible true 4.5 source-wind / 5.2 rigid-wind comparison; NEVER a collision release."""
import hashlib,json,math,sys
from pathlib import Path
# Blender's --python does not necessarily put the source script directory on sys.path.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pony_source_trajectory import classify,xyz

SCHEMA="equine.pony.45_wind_source_48f.v1"
QUALITY="equine.pony.45_to_52_wind_on_interop.v1"
def weights(names,vals):
    if type(names)!=list or len(names)!=9 or len(set(names))!=9 or any(type(n)!=str or not n.startswith("wind_") for n in names):
        raise ValueError("incorrect original wind source names")
    if type(vals)!=list or len(vals)!=9 or any(type(v) not in (int,float) or not math.isfinite(v) or v < -1e-7 or v>1.00001 for v in vals):
        raise ValueError("invalid actual wind source weights")
    return dict(zip(names,[float(x) for x in vals]))
def length(a,b):
    return math.dist(a,b)
def p95(xs):
    if not xs or any(not math.isfinite(x) or x<0 for x in xs):raise ValueError("invalid original source discrepancy")
    return sorted(xs)[math.ceil(len(xs)*.95)-1]
def compare(skin,source45,rigid52):
    gate=classify(skin)
    ids={g["card_id"]:g for g in skin["guides"]}
    expected={"schema","source_kind","source_blend_sha256","source_capsule_sha256","rig","frame_count","source_surface","wind_names","frames","source_mutated_on_disk","scientific_hold","release_admission"}
    if type(source45)!=dict or set(source45)!=expected or source45["schema"]!=SCHEMA or source45["source_kind"]!="original_synthetic" or source45["rig"]!="PonyRig30" or source45["source_surface"]!="geometric_coat_mane_tail" or source45["frame_count"]!=48:
        raise ValueError("not exact original 4.5 wind capture")
    if source45["source_blend_sha256"]!=skin["source_blend_sha256"] or source45["source_capsule_sha256"]!=gate["source_capsule_sha256"]:
        raise ValueError("wind-active capture not SHA-matched")
    if source45["source_mutated_on_disk"] is not False or source45["scientific_hold"]!="KEEP" or source45["release_admission"] is not False:raise ValueError("source mutation or unsafe admission")
    if type(rigid52)!=dict or rigid52.get("schema")!="equine.pony52.attached_original_groom_48f.v1" or rigid52.get("mode")!="animation" or rigid52.get("modifier_mode")!="Animation":
        raise ValueError("not original rigid 5.2 negative-control class")
    if rigid52.get("source_blend_sha256")!=skin["source_blend_sha256"] or rigid52.get("source_capsule_sha256")!=gate["source_capsule_sha256"] or rigid52.get("source_wind_morph_mode")!="animated":
        raise ValueError("5.2 source/morph state not SHA-matched")
    if rigid52.get("source_surface")!="geometric_coat_mane_tail" or rigid52.get("source_wind_morphs_detected")!=9 or rigid52.get("source_surface_has_armature_skin") is not True or rigid52.get("curves_surface_binding_confirmed") is not True:
        raise ValueError("not direct source-attached 5.2 animated groom")
    if rigid52.get("status")!="48F_ORIGINAL_SKIN_GROOM_NATIVE_GEOMETRY_OBSERVED" or rigid52.get("errors") or rigid52.get("science_hold")!="KEEP" or rigid52.get("release_admission") is not False or rigid52.get("full_body_collision_accepted") is not False:
        raise ValueError("native source or science gate failed")
    if rigid52.get("frame_count")!=48 or rigid52.get("guide_count")!=6:raise ValueError("wrong guide/frame cardinality")
    f45,f52=source45["frames"],rigid52["frames"]
    w52=rigid52.get("source_wind_effective_weights_per_frame"); n52=rigid52.get("source_wind_key_names")
    if type(f45)!=list or type(f52)!=list or len(f45)!=48 or len(f52)!=48 or type(w52)!=list or len(w52)!=48:raise ValueError("incomplete 48-frame wind source")
    region=("mane","forelock","tail")
    errroot={k:[] for k in region};errdir={k:[] for k in region};effect={k:[] for k in region};hits={k:0 for k in region}
    peak=0.
    for i,(a,b,wb) in enumerate(zip(f45,f52,w52)):
        if type(a)!=dict or set(a)!={"frame","wind_weights","guides"} or a["frame"]!=i+1 or type(b)!=dict or b.get("frame")!=i+1:
            raise ValueError("reordered native wind observation")
        wa=weights(source45["wind_names"],a["wind_weights"]);wb=weights(n52,wb)
        if set(wa)!=set(wb) or any(abs(wa[k]-wb[k])>1e-5 for k in wa):raise ValueError("full nine-channel cross-version wind policy differs")
        peak=max(peak,*wa.values())
        if type(a["guides"])!=list or type(b.get("guides"))!=list or len(a["guides"])!=6 or len(b["guides"])!=6:
            raise ValueError("lost source guides")
        ga={q.get("card_id"):q for q in a["guides"] if type(q)==dict};gb={q.get("card_id"):q for q in b["guides"] if type(q)==dict}
        if len(ga)!=6 or len(gb)!=6 or set(ga)!=set(ids) or set(gb)!=set(ids):raise ValueError("duplicate/missing source guide")
        for card,g in ids.items():
            x,y=ga[card],gb[card]
            if set(x)!={"card_id","region","root_m","tip_m"} or x["region"]!=g["region"] or y.get("region")!=g["region"]:
                raise ValueError("false original region")
            aroot,atip=xyz(x["root_m"]),xyz(x["tip_m"])
            broot,btip=xyz(y["actual_root_m"]),xyz(y["actual_tip_m"])
            rel=xyz(y["tip_minus_root_m"])
            if length(btip,tuple(broot[j]+rel[j] for j in range(3)))>2e-6:raise ValueError("5.2 relative tip falsified")
            reg=g["region"]
            errroot[reg].append(length(aroot,broot))
            adir=tuple(atip[j]-aroot[j] for j in range(3))
            errdir[reg].append(length(adir,rel))
            ref=g["samples"][i]
            effect[reg].append(length(adir,tuple(ref["tip_m"][j]-ref["root_m"][j] for j in range(3))))
            n=y.get("segment_surface_ray_hits")
            if type(n)!=int or not 0<=n<=50:raise ValueError("invalid native contact candidate")
            hits[reg]+=n
    verdict=("INCONCLUSIVE_NO_ACTIVATED_WIND" if peak<=.01 else
             "SOURCE_WIND_ANIMATION_MATCHES_RIGID_52_ENGINEERING_ONLY" if max(max(v) for v in errroot.values())<=.005 and max(p95(v) for v in errdir.values())<=.005 else
             "SOURCE_WIND_ANIMATION_CROSS_VERSION_DISCREPANCY_SCIENCE_HOLD")
    return {"schema":QUALITY,"source_blend_sha256":skin["source_blend_sha256"],"source_capsule_sha256":gate["source_capsule_sha256"],
        "frames":48,"guides":6,"max_wind_weight":round(peak,7),
        "max_root_45_vs_52_m_by_region":{k:round(max(v),8) for k,v in errroot.items()},
        "p95_tip_vector_45_vs_52_m_by_region":{k:round(p95(v),8) for k,v in errdir.items()},
        "max_wind_effect_45_vs_skin_only_m_by_region":{k:round(max(v),8) for k,v in effect.items()},
        "potential_body_ray_hits_by_region":hits,"verdict":verdict,"source_mutated_on_disk":False,
        "collision_signed_depth_qualified":False,"visual_material_accepted":False,"scientific_hold":"KEEP","release_or_CPE_admission":False}
def native(args):
    import bpy
    if len(args)!=3:raise SystemExit("usage: --native original45.blend skin_capsule.json output.json")
    source,capsule_path,out=map(Path,args)
    if not source.is_file() or not capsule_path.is_file() or out.exists() or not 4096<source.stat().st_size<300000000:
        raise ValueError("source absent/unbounded or output overwrite")
    skin=json.loads(capsule_path.read_text());gate=classify(skin)
    if hashlib.sha256(source.read_bytes()).hexdigest()!=skin["source_blend_sha256"] or bpy.app.version[:3]!=(4,5,15):
        raise ValueError("not byte SHA pinned Blender 4.5.15 original")
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
    rig=bpy.data.objects.get("PonyRig30");groom=bpy.data.objects.get("geometric_coat_mane_tail")
    if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=30 or groom is None or groom.type!="MESH" or len(groom.data.vertices)!=10500:
        raise ValueError("not actual original skinned 30j groom")
    if not any(m.type=="ARMATURE" and m.object==rig for m in groom.modifiers):raise ValueError("source skin absent")
    keys=[k for k in groom.data.shape_keys.key_blocks if k.name.startswith("wind_")] if groom.data.shape_keys else []
    if len(keys)!=9:raise ValueError("nine baked source morphs absent")
    obj={"schema":SCHEMA,"source_kind":"original_synthetic","source_blend_sha256":skin["source_blend_sha256"],
         "source_capsule_sha256":gate["source_capsule_sha256"],"rig":"PonyRig30","frame_count":48,
         "source_surface":"geometric_coat_mane_tail","wind_names":[k.name for k in keys],"frames":[],
         "source_mutated_on_disk":False,"scientific_hold":"KEEP","release_admission":False}
    for frame in range(1,49):
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        w=[float(k.value) for k in keys];weights(obj["wind_names"],w)
        ev=groom.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
        if mesh is None or len(mesh.vertices)!=10500:raise ValueError("evaluated original skin/groom invalid")
        try:
            mat=ev.matrix_world;row=[]
            for g in skin["guides"]:
                i=10*g["card_id"]
                root=mat@((mesh.vertices[i].co+mesh.vertices[i+1].co)*.5)
                tip=mat@((mesh.vertices[i+8].co+mesh.vertices[i+9].co)*.5)
                row.append({"card_id":g["card_id"],"region":g["region"],"root_m":[float(v) for v in root],"tip_m":[float(v) for v in tip]})
            obj["frames"].append({"frame":frame,"wind_weights":w,"guides":row})
        finally:ev.to_mesh_clear()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")
    print("ORIGINAL_45_NINE_WIND_KEYS_NATIVE_48F_NOT_RELEASE",obj["source_blend_sha256"])
def normalize_args(argv):
    # Blender keeps its own flags and the literal '--' in sys.argv.
    return argv[argv.index("--")+1:] if "--" in argv else argv
def main(argv):
    argv=normalize_args(argv)
    if len(argv)==4 and argv[0]=="--native":native(argv[1:]);return
    if len(argv)==5 and argv[0]=="--compare":
        source,src45,rigid=[json.loads(Path(p).read_text()) for p in argv[1:4]]
        out=Path(argv[4])
        if out.exists():raise ValueError("refuse evidence overwrite")
        result=compare(source,src45,rigid);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        print("WIND_ACTIVE_ORIGINAL45_VS_52_RIGID_48F_SCIENCE_HELD",json.dumps(result,sort_keys=True))
        return
    raise SystemExit("usage: --native original.blend capsule.json output.json | --compare capsule.json original45_wind.json animation52.json output.json")
if __name__=="__main__":main(sys.argv[1:])
