"""N03D-AC genuine source 60Hz FK and target MPFB/skinned shoe matched-time witness.

Diagnostic only. Does not invent anatomical heel/toe or ground-force observations.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE))
from trace import assess
sys.path.insert(0,str(HERE.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh, git_blob_sha, SOURCES, fk

def require(ok, code):
    if not ok: raise RuntimeError(code)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def pos(rig,bone):
    p=rig.matrix_world@rig.pose.bones[bone].head
    return [float(p.x),float(p.y),float(p.z)]

def shoe_sides(shoe):
    xs=[float(v.co.x) for v in shoe.data.vertices]
    mid=(min(xs)+max(xs))/2
    return {
        "L":[i for i,x in enumerate(xs) if x>=mid],
        "R":[i for i,x in enumerate(xs) if x<mid],
    }

def sole_minimum(shoe, sides):
    deps=bpy.context.evaluated_depsgraph_get()
    obj=shoe.evaluated_get(deps)
    mesh=obj.to_mesh()
    try:
        require(len(mesh.vertices)==len(shoe.data.vertices),"SHOE_VERTEX_ID_DRIFT")
        xyz=[obj.matrix_world@v.co for v in mesh.vertices]
        return {side:float(min(xyz[k].z for k in ids)) for side,ids in sides.items()}
    finally:
        obj.to_mesh_clear()

def main():
    p=argparse.ArgumentParser()
    for name in ("scene","sha","wardrobe","retarget","trace","source","out"):
        p.add_argument("--"+name,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    require(sha(a.scene)==a.sha,"SOURCE_SCENE_SHA")
    sc=bpy.context.scene
    require(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
            sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","RIGHTS_ORIGINAL_ONLY")
    require((sc.frame_start,sc.frame_end,sc.render.fps)==(0,71,12),"SOURCE_SCENE_CLOCK")
    ward=json.loads(Path(a.wardrobe).read_text())
    rec=json.loads(Path(a.retarget).read_text())
    trace=json.loads(Path(a.trace).read_text())
    require(rec["candidate_blend_sha256"]==a.sha and rec["input_scene_sha256"]==ward["blend_sha256"]
            and trace["source_scene_sha256"]==a.sha,"EXACT_SOURCE_JOIN")
    raw=Path(a.source).read_bytes()
    require(Path(a.source).name=="Neutral_FW.bvh" and git_blob_sha(raw)==SOURCES["Neutral_FW.bvh"] and
            sha(a.source)==trace["source_100style_sha256"],"BVH_PIN_MISMATCH")
    src=parse_bvh(raw)
    require(src["count"]==2400,"SOURCE_CLIP_LENGTH")
    actors=[]
    for owner in ward["characters"]:
        name=owner["name"]
        require(name in ("AsterOriginal","JuniperOriginal"),"UNAPPROVED_ACTOR")
        rig=bpy.data.objects.get(name+"_MPFBRig")
        require(rig is not None and len(rig.data.bones)==163,"TARGET_REAL_RIG")
        shoe_rows=[g for g in owner["garments"] if g["pack"]=="shoes01"]
        require(len(shoe_rows)==1,"REAL_CC0_SHOES")
        shoe=bpy.data.objects.get(shoe_rows[0]["native_object"])
        require(shoe is not None and any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers),
                "REAL_SKINNED_SHOE")
        sides=shoe_sides(shoe)
        require(all(len(ids)>100 for ids in sides.values()),"SHOE_SEGMENT_INVALID")
        observed={"L":[],"R":[]}
        for n in range(360):
            sec=n/60
            scene_frame=sec*12
            frame=int(math.floor(scene_frame+1e-9))
            sc.frame_set(frame,subframe=scene_frame-frame)
            bpy.context.view_layer.update()
            source=fk(src,120+n)
            source_hip=[float(x)/100 for x in source["Hips"]]
            hip=tuple((v+w)/2 for v,w in zip(pos(rig,"pelvis.L"),pos(rig,"pelvis.R")))
            shoe_min=sole_minimum(shoe,sides)
            for side,tag in (("L","Left"),("R","Right")):
                observed[side].append({
                    "index":n,"time_s":sec,
                    "source_hip":source_hip,
                    "source_ankle":[float(x)/100 for x in source[tag+"Ankle"]],
                    "source_toe":[float(x)/100 for x in source[tag+"Toe"]],
                    "target_hip":list(hip),
                    "target_foot":pos(rig,"foot."+side),
                    "target_shoe_min_z":shoe_min[side],
                })
        actors.append({"name":name,"sides":observed})
    require(sorted(a["name"] for a in actors)==["AsterOriginal","JuniperOriginal"],"ACTOR_INCOMPLETE")
    report={"schema":"scp.n03d-ac.matched-source-to-bone-60hz.v1",
            "source_class":"ORIGINAL_FICTIONAL_CC0",
            "source_scene_sha256":a.sha,"source_motion_sha256":sha(a.source),
            "source_shoe_trace_sha256":sha(a.trace),"source_motion_changed":False,
            "mvp_accepted":False,"source_to_target_anatomical_labels_verified":False,
            "source_near_ground_is_not_force_contact":True,
            "shoe_partition_is_not_anatomical_heel_toe":True,
            "time_sample_count_per_side":360,"timebase_hz":60,
            "actors":actors}
    Path(a.out).write_text(json.dumps(report,sort_keys=True,allow_nan=False)+"\n")
    decision=assess(report)
    target=str(Path(a.out).with_suffix(".diagnosis.json"))
    Path(target).write_text(json.dumps(decision,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_AC_MATCHED_NATIVE_CAUSAL_WITNESS",json.dumps(decision,sort_keys=True),flush=True)
    require(decision["status"]=="HOLD" and len(decision["results"])==4,"FALSE_PHYSICAL_ACCEPTANCE")

if __name__=="__main__":main()
