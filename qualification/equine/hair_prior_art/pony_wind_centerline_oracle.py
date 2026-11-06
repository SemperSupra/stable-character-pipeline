#!/usr/bin/env python3
"""Matched 48f five-row source card versus six-control-point attached-curve oracle.

Never promotes experimental hair physics, material or biological adequacy.
Standalone Blender 4.5/5.2 native source observers share this geometry ABI.
"""
import hashlib
import json
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pony_source_trajectory import classify,xyz
from pony_wind_state_interop import weights,p95
from pony_wind_groom_transfer import compare as prior_compare

ROW_SCHEMA="equine.pony.wind_source_five_rows_48f.v1"
CURVE_SCHEMA="equine.pony52.wind_curve_six_points_48f.v1"
QUALITY_SCHEMA="equine.pony.wind_five_row_vs_six_curve_48f.v1"
REGIONS=("mane","forelock","tail")

def positions(items,n):
    if type(items)!=list or len(items)!=n:
        raise ValueError("wrong original centerline point cardinality")
    return [xyz(v) for v in items]

def arc(points):
    return sum(math.dist(points[i-1],points[i]) for i in range(1,len(points)))

def sampled_index(points,n=6):
    # Exactly the same j*4/5 index-linear rest construction as the 5.2
    # native adapter, not a physically material-conserving interpolation.
    if len(points)!=5 or n!=6:raise ValueError("unrecognized original grid")
    out=[]
    for i in range(n):
        t=4*i/(n-1);k=min(3,int(t));v=t-k
        out.append(tuple(points[k][d]*(1-v)+points[k+1][d]*v for d in range(3)))
    return out

def sampled_arclength(points,n=6):
    if len(points)!=5 or n!=6:raise ValueError("unrecognized original grid")
    s=[0.]
    for i in range(1,len(points)):
        s.append(s[-1]+math.dist(points[i-1],points[i]))
    if s[-1]<.01 or s[-1]>3:raise ValueError("unusable source strand arc")
    out=[]
    for j in range(n):
        distance=s[-1]*j/(n-1)
        k=next((i for i in range(4) if distance<=s[i+1]),3)
        amount=(distance-s[k])/(s[k+1]-s[k]) if s[k+1]>s[k]+1e-9 else 0.
        out.append(tuple(points[k][d]*(1-amount)+points[k+1][d]*amount for d in range(3)))
    return out

def new_row_receipt(skin,blender_version,wind_names):
    gate=classify(skin)
    if blender_version not in ("4.5.15","5.2.3"):
        raise ValueError("unsupported original native source version")
    weights(wind_names,[0.]*9)
    return {"schema":ROW_SCHEMA,"original_blender_version":blender_version,
        "source_kind":"original_synthetic","source_blend_sha256":skin["source_blend_sha256"],
        "source_capsule_sha256":gate["source_capsule_sha256"],
        "rig":"PonyRig30","frame_count":48,"guide_count":6,"point_count":5,
        "source_surface":"geometric_coat_mane_tail","wind_names":wind_names[:],"frames":[],
        "source_mutated_on_disk":False,"scientific_hold":"KEEP","release_admission":False}

def new_curve_receipt(capsule,wind_names):
    gate=classify(capsule);weights(wind_names,[0.]*9)
    return {"schema":CURVE_SCHEMA,"original_blender_version":"5.2.3",
        "source_kind":"original_synthetic","source_blend_sha256":capsule["source_blend_sha256"],
        "source_capsule_sha256":gate["source_capsule_sha256"],
        "rig":"PonyRig30","frame_count":48,"guide_count":6,"point_count":6,
        "source_surface":"geometric_coat_mane_tail","mode":"animation","source_wind_morph_mode":"animated",
        "wind_names":wind_names[:],"frames":[],"source_mutated_on_disk":False,
        "scientific_hold":"KEEP","release_admission":False}

def check_receipt(receipt,kind,version,skin):
    gate=classify(skin)
    common={"schema","original_blender_version","source_kind","source_blend_sha256",
        "source_capsule_sha256","rig","frame_count","guide_count","point_count",
        "source_surface","wind_names","frames","source_mutated_on_disk",
        "scientific_hold","release_admission"}
    expected=common if kind=="rows" else common|{"mode","source_wind_morph_mode"}
    n=5 if kind=="rows" else 6
    schema=ROW_SCHEMA if kind=="rows" else CURVE_SCHEMA
    if type(receipt)!=dict or set(receipt)!=expected:
        raise ValueError("extra or missing original point-trace metadata")
    if receipt["schema"]!=schema or receipt["original_blender_version"]!=version:
        raise ValueError("unexpected original Blender source version")
    if receipt["source_blend_sha256"]!=skin["source_blend_sha256"] or receipt["source_capsule_sha256"]!=gate["source_capsule_sha256"]:
        raise ValueError("not the same exact original pony source and capsule")
    if receipt["source_kind"]!="original_synthetic" or receipt["rig"]!="PonyRig30" or receipt["source_surface"]!="geometric_coat_mane_tail":
        raise ValueError("trace not original 30-joint skinned source")
    if receipt["frame_count"]!=48 or receipt["guide_count"]!=6 or receipt["point_count"]!=n or receipt["scientific_hold"]!="KEEP" or receipt["release_admission"] is not False or receipt["source_mutated_on_disk"] is not False:
        raise ValueError("incomplete cardinality or bypassed science hold")
    if kind=="curve" and (receipt["mode"]!="animation" or receipt["source_wind_morph_mode"]!="animated"):
        raise ValueError("hair point trace not exact wind-active Animation control")
    weights(receipt["wind_names"],[0.]*9)
    if type(receipt["frames"])!=list or len(receipt["frames"])!=48:
        raise ValueError("not all original 48 native frames")
    identity={g["card_id"]:g["region"] for g in skin["guides"]}
    frames=[]
    for i,frame in enumerate(receipt["frames"]):
        if type(frame)!=dict or set(frame)!={"frame","wind_weights","guides"} or type(frame["frame"])!=int or frame["frame"]!=i+1:
            raise ValueError("original native frame misordered or unknown")
        w=weights(receipt["wind_names"],frame["wind_weights"])
        if type(frame["guides"])!=list or len(frame["guides"])!=6:
            raise ValueError("point witness guide cardinality broken")
        mapped={}
        for g in frame["guides"]:
            if type(g)!=dict or set(g)!={"card_id","region","points_world_m"}:
                raise ValueError("unknown original point witness fields")
            card=g["card_id"]
            if type(card)!=int or card not in identity or card in mapped or g["region"]!=identity[card]:
                raise ValueError("forged or repeated original card owner")
            pts=positions(g["points_world_m"],n)
            if arc(pts)<.01 or arc(pts)>3:
                raise ValueError("collapsed or unbounded original centerline")
            mapped[card]=pts
        if set(mapped)!=set(identity):raise ValueError("missing original card")
        frames.append((w,mapped))
    return frames

def compare(skin,source45,bare52,curves52,row45,row52,curvepoints52):
    # Existing three-way root/tip oracle is a required input, not silently
    # replaced by the new five-row/two-parameterization observer.
    staged=prior_compare(skin,source45,bare52,curves52)
    obs45=check_receipt(row45,"rows","4.5.15",skin)
    obs52=check_receipt(row52,"rows","5.2.3",skin)
    obsc=check_receipt(curvepoints52,"curve","5.2.3",skin)
    ids={g["card_id"]:g["region"] for g in skin["guides"]}
    source_deltas={r:[] for r in REGIONS}
    curve_index_deltas={r:[] for r in REGIONS}
    curve_arclength_sample_errors={r:[] for r in REGIONS}
    source_arc_deltas={r:[] for r in REGIONS}
    curve_arclength_difference={r:[] for r in REGIONS}
    root_deltas={r:[] for r in REGIONS}
    ref_arc={r:[] for r in REGIONS}
    for fi,(a,b,c) in enumerate(zip(obs45,obs52,obsc)):
        raw45,pts45=a;raw52,pts52=b;rawc,ptsc=c
        direct=[
            weights(source45["wind_names"],source45["frames"][fi]["wind_weights"]),
            weights(bare52["wind_names"],bare52["frames"][fi]["wind_weights"]),
            weights(curves52["source_wind_key_names"],curves52["source_wind_effective_weights_per_frame"][fi])]
        if any(set(d)!=set(raw45) or any(abs(d[k]-raw45[k])>1e-5 for k in raw45) for d in [raw52,rawc]+direct):
            raise ValueError("five native wind states differ")
        def as_map(frame):
            got={x["card_id"]:x for x in frame["guides"]}
            if len(got)!=6 or set(got)!=set(ids):
                raise ValueError("original corroborating source guide missing")
            return got
        prior45=as_map(source45["frames"][fi]);prior52=as_map(bare52["frames"][fi]);priorc=as_map(curves52["frames"][fi])
        for card,region in ids.items():
            p45,p52,pc=pts45[card],pts52[card],ptsc[card]
            for p,rec in ((p45,prior45[card]),(p52,prior52[card])):
                if math.dist(p[0],xyz(rec["root_m"]))>2e-6 or math.dist(p[-1],xyz(rec["tip_m"]))>2e-6:
                    raise ValueError("five-row source witness disagrees with original independent root/tip")
            g=priorc[card]
            if math.dist(pc[0],xyz(g["actual_root_m"]))>2e-6 or math.dist(pc[-1],xyz(g["actual_tip_m"]))>2e-6:
                raise ValueError("curve witness disagrees with original independent root/tip")
            if abs(arc(pc)-g["curve_polyline_length_m"])>2e-6:
                raise ValueError("original curve six-point arc receipt falsified")
            root_deltas[region].append(math.dist(p52[0],pc[0]))
            source_arc_deltas[region].append(abs(arc(p45)-arc(p52)))
            curve_arclength_difference[region].append(abs(arc(p52)-arc(pc)))
            ref_arc[region].append(arc(p52))
            for j in range(5):
                v45=tuple(p45[j][d]-p45[0][d] for d in range(3))
                v52=tuple(p52[j][d]-p52[0][d] for d in range(3))
                source_deltas[region].append(math.dist(v45,v52))
            for sampled,output in ((sampled_index(p52),curve_index_deltas),(sampled_arclength(p52),curve_arclength_sample_errors)):
                for j in range(1,6):
                    a=tuple(sampled[j][d]-sampled[0][d] for d in range(3))
                    b=tuple(pc[j][d]-pc[0][d] for d in range(3))
                    output[region].append(math.dist(a,b))
    p95_by_region=lambda m:{r:round(p95(m[r]),8) for r in REGIONS}
    max_by_region=lambda m:{r:round(max(m[r]),8) for r in REGIONS}
    avg_by_region=lambda m:{r:round(sum(m[r])/len(m[r]),8) for r in REGIONS}
    mismatch_source=p95_by_region(source_deltas)
    mismatch_curve=p95_by_region(curve_index_deltas)
    mismatch_arc=p95_by_region(curve_arclength_sample_errors)
    root=max_by_region(root_deltas)
    if not staged["observed_original_wind_activity"]:
        verdict="INCONCLUSIVE_NO_WIND_EXCITATION_SCIENCE_HOLD"
    elif max(mismatch_source.values())>.005:
        verdict="FIVE_ROW_ORIGINAL_SOURCE_DIFFERS_ACROSS_BLENDER_VERSIONS_HOLD"
    elif max(root.values())>.005:
        verdict="FOLLICLE_ROOT_TRANSPORT_DIFFERENCE_SCIENCE_HOLD"
    elif max(mismatch_curve.values())>.005:
        verdict="DISTRIBUTED_FIVE_ROW_TO_SIX_CURVE_TRANSFER_DIFFERENCE_SCIENCE_HOLD"
    else:
        verdict="INDEX_LINEAR_SOURCE_POINTS_MATCH_CURVE_ENGINEERING_ONLY"
    return {"schema":QUALITY_SCHEMA,"source_blend_sha256":skin["source_blend_sha256"],
        "source_capsule_sha256":classify(skin)["source_capsule_sha256"],
        "frames":48,"guides":6,"source_rows":5,"curve_points":6,"wind_key_count":9,
        "original_45_to_bare_52_five_row_relative_p95_m_by_region":mismatch_source,
        "source_52_to_curve_52_index_resampled_point_p95_m_by_region":mismatch_curve,
        "source_52_to_curve_52_arclength_resampled_point_p95_m_by_region":mismatch_arc,
        "source_45_to_52_five_row_arc_abs_max_m_by_region":max_by_region(source_arc_deltas),
        "source_52_to_curve_52_arc_abs_max_m_by_region":max_by_region(curve_arclength_difference),
        "source_52_mean_five_row_arc_m_by_region":avg_by_region(ref_arc),
        "source_52_to_curve_52_root_max_m_by_region":root,
        "verdict":verdict,"full_nine_wind_channels_same_value_per_frame":True,
        "physical_material_accepted":False,"body_collision_signed_accepted":False,
        "visual_accepted":False,"source_mutated_on_disk":False,
        "scientific_hold":"KEEP","release_or_CPE_admission":False}

def native(args):
    import bpy
    if len(args)!=3:raise SystemExit("usage: --native original.blend source_capsule.json out.json")
    source,capsule_path,out=map(Path,args)
    if not source.is_file() or not capsule_path.is_file() or out.exists() or not 4096<source.stat().st_size<300000000:
        raise ValueError("source absent, unbounded, or witness overwrite")
    skin=json.loads(capsule_path.read_text())
    versions={(4,5,15):"4.5.15",(5,2,3):"5.2.3"}
    version=versions.get(bpy.app.version[:3])
    if version is None or hashlib.sha256(source.read_bytes()).hexdigest()!=skin["source_blend_sha256"]:
        raise ValueError("invalid native Blender source version/bytes")
    trace=None
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
    rig=bpy.data.objects.get("PonyRig30")
    groom=bpy.data.objects.get("geometric_coat_mane_tail")
    if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=30 or groom is None or groom.type!="MESH" or len(groom.data.vertices)!=10500 or len(groom.data.polygons)!=8400:
        raise ValueError("actual 30j pony original groom topology absent")
    if not any(m.type=="ARMATURE" and m.object==rig for m in groom.modifiers):
        raise ValueError("original native groom has no source armature")
    keys=[k for k in groom.data.shape_keys.key_blocks if k.name.startswith("wind_")] if groom.data.shape_keys else []
    trace=new_row_receipt(skin,version,[k.name for k in keys])
    scene=bpy.context.scene
    scene.frame_set(0);scene.frame_set(1)
    for f in range(1,49):
        scene.frame_set(f);bpy.context.view_layer.update()
        active=[float(k.value) for k in keys]
        weights(trace["wind_names"],active)
        ev=groom.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=ev.to_mesh()
        if mesh is None or len(mesh.vertices)!=10500:
            raise ValueError("source evaluated pony centerline topology lost")
        try:
            m=ev.matrix_world.copy()
            guides=[]
            for guide in skin["guides"]:
                card=guide["card_id"];points=[]
                for row in range(5):
                    k=card*10+2*row
                    p=m@((mesh.vertices[k].co+mesh.vertices[k+1].co)*.5)
                    points.append([float(v) for v in p])
                guides.append({"card_id":card,"region":guide["region"],"points_world_m":points})
            trace["frames"].append({"frame":f,"wind_weights":active,"guides":guides})
        finally:ev.to_mesh_clear()
    if hashlib.sha256(source.read_bytes()).hexdigest()!=skin["source_blend_sha256"]:
        raise ValueError("original .blend mutated on disk during observation")
    check_receipt(trace,"rows",version,skin)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(trace,sort_keys=True,indent=2)+"\n")
    print("ORIGINAL_NATIVE_FIVE_ROW_48F_SCIENCE_HELD",json.dumps({
        "engine":version,"frames":48,"guides":6,"source":skin["source_blend_sha256"]},sort_keys=True))

def main(argv):
    argv=argv[argv.index("--")+1:] if "--" in argv else argv
    if len(argv)==4 and argv[0]=="--native":return native(argv[1:])
    if len(argv)==9 and argv[0]=="--compare":
        skin,source45,bare52,curves52,row45,row52,curvepoints52=[
            json.loads(Path(f).read_text()) for f in argv[1:8]]
        out=Path(argv[8])
        if out.exists():raise ValueError("refuse to overwrite native evidence")
        receipt=compare(skin,source45,bare52,curves52,row45,row52,curvepoints52)
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
        print("ORIGINAL_WIND_FIVE_ROW_TO_SIX_CURVE_EVIDENCE_SCIENCE_HELD",json.dumps(receipt,sort_keys=True))
        return
    raise SystemExit("usage: --native original.blend capsule.json out.json | --compare skin.json 45wind.json 52bare.json 52curves.json 45rows.json 52rows.json 52points.json out.json")

if __name__=="__main__":main(sys.argv[1:])
