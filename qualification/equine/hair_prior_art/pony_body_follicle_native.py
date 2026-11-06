#!/usr/bin/env python3
"""Native 4.5 original Shetland body/follicle nearest-face witness.

Produces a reversible projection *proposal*, not body-follicle snapping. Uses
source-exact six cards×48f and original rigged torso/head/neck/hind limb meshes.
Rest f1 face IDs, barycentric weights and vertex IDs persist over time; body
meshes remain physically separate (not certified as closed volume).
"""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pony_source_trajectory import classify as classify_source
from pony52_actual_surface_native import REGION_TARGETS

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=3:
    raise SystemExit("usage: blender -b --python pony_body_follicle_native.py -- original.blend source_capsule.json out.json")
source,source_file,out=map(Path,sys.argv[sys.argv.index("--")+1:])
if not source.is_file() or not source_file.is_file() or out.exists():
    raise ValueError("original source absent or overwriting scientific evidence")
if not 4096<source.stat().st_size<300000000:
    raise ValueError("original .blend unexpected bytes")
capsule=json.loads(source_file.read_text())
contract=classify_source(capsule)
if hashlib.sha256(source.read_bytes()).hexdigest()!=capsule["source_blend_sha256"]:
    raise ValueError("source .blend and follicle capsule digest mismatch")
out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
rig=bpy.data.objects.get("PonyRig30")
if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=30:
    raise ValueError("source 30j articulated pony missing")
source_names=sorted({name for group in REGION_TARGETS.values() for name in group})
objects={n:bpy.data.objects.get(n) for n in source_names}
if any(o is None or o.type!="MESH" for o in objects.values()):
    raise ValueError("one or more original body mesh areas absent")
scene=bpy.context.scene
def bary(p,a,b,c):
    ab=b-a;ac=c-a;ap=p-a
    d00=ab.dot(ab);d01=ab.dot(ac);d11=ac.dot(ac)
    d20=ap.dot(ab);d21=ap.dot(ac)
    denom=d00*d11-d01*d01
    if not math.isfinite(denom) or denom<1e-12:
        raise ValueError("degenerate original body surface triangle")
    v=(d11*d20-d01*d21)/denom
    w=(d00*d21-d01*d20)/denom
    u=1-v-w
    if any(not math.isfinite(x) or not -1e-4<=x<=1.0001 for x in (u,v,w)):
        raise ValueError("nearest surface point not in selected source triangle")
    if abs(u+v+w-1)>1e-6:raise ValueError("not barycentric")
    return (float(u),float(v),float(w))
def bodydata():
    deps=bpy.context.evaluated_depsgraph_get()
    result={}
    for name,obj in objects.items():
        evaluated=obj.evaluated_get(deps)
        mesh=evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            v=[evaluated.matrix_world @ pt.co for pt in mesh.vertices]
            faces=[tuple(face.vertices) for face in mesh.loop_triangles]
            if len(v)<3 or not faces or any(len(face)!=3 or any(i>=len(v) for i in face) for face in faces):
                raise ValueError("body source has invalid topology")
            tree=BVHTree.FromPolygons(v,faces,all_triangles=True)
            result[name]={"vertices":v,"faces":faces,"tree":tree}
        finally:
            evaluated.to_mesh_clear()
    return result
anchors={}
records=[{"card_id":g["card_id"],"region":g["region"],"owner_bone":g["owner_bone"],"frames":[]}
         for g in capsule["guides"]]
for frame in range(1,49):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    bodies=bodydata()
    if frame==1:
        for g in capsule["guides"]:
            root=Vector(g["samples"][0]["root_m"])
            candidates=[]
            for n in REGION_TARGETS[g["region"]]:
                p,normal,face,dist=bodies[n]["tree"].find_nearest(root)
                if p is None or face is None or not math.isfinite(dist):
                    raise ValueError("no nearest rest body skin for hair card")
                candidates.append((float(dist),n,int(face),p,normal))
            dist,n,face,p,normal=min(candidates,key=lambda x:(x[0],x[1],x[2]))
            mesh=bodies[n]
            vids=mesh["faces"][face]
            weights=bary(p,*[mesh["vertices"][i] for i in vids])
            anchor=sum((mesh["vertices"][vid]*weights[i] for i,vid in enumerate(vids)),Vector((0.,0.,0.)))
            if (anchor-p).length>1e-5:
                raise ValueError("rest barycentric point reconstruction false")
            anchors[g["card_id"]]={
                "source_body_object":n,"rest_triangle_index":face,
                "rest_triangle_vertex_ids":list(vids),"rest_barycentric":list(weights),
                "rest_projection_m":[float(x) for x in anchor],
                "rest_root_to_skin_distance_m":dist,
                "rest_normal_m":[float(x) for x in normal.normalized()],
                "rest_root_minus_anchor_m":[float(x) for x in root-anchor]}
    for g,rec in zip(capsule["guides"],records):
        card=g["card_id"]
        expected=g["samples"][frame-1]
        root=Vector(expected["root_m"])
        sampled=[]
        for n in REGION_TARGETS[g["region"]]:
            p,normal,face,dist=bodies[n]["tree"].find_nearest(root)
            if p is None or not math.isfinite(dist) or face is None:
                raise ValueError("nonfinite source body nearest at frame "+str(frame))
            sampled.append((float(dist),n,int(face),p,normal))
        dist,n,face,p,normal=min(sampled,key=lambda x:(x[0],x[1],x[2]))
        geo=bodies[n]
        vids=geo["faces"][face]
        near_weights=bary(p,*[geo["vertices"][i] for i in vids])
        rest=anchors[card]
        anchor_obj=bodies[rest["source_body_object"]]
        fixed_index=rest["rest_triangle_index"]
        if fixed_index>=len(anchor_obj["faces"]) or tuple(rest["rest_triangle_vertex_ids"])!=anchor_obj["faces"][fixed_index]:
            raise ValueError("source anatomy face topology changed across rig poses")
        fixed=sum((anchor_obj["vertices"][vid]*rest["rest_barycentric"][i] for i,vid in enumerate(rest["rest_triangle_vertex_ids"])),Vector((0.,0.,0.)))
        offset=Vector(rest["rest_root_minus_anchor_m"])
        rec["frames"].append({
            "frame":frame,"source_root_m":expected["root_m"],
            "nearest_body_object":n,"nearest_face_index":face,
            "nearest_face_vertex_ids":list(vids),"nearest_barycentric":list(near_weights),
            "nearest_body_point_m":[float(x) for x in p],
            "nearest_surface_normal":[float(x) for x in normal.normalized()],
            "nearest_unsigned_distance_m":dist,
            "normal_directional_offset_m":float((root-p).dot(normal.normalized())),
            "rest_persistent_anchor_point_m":[float(x) for x in fixed],
            "rest_anchor_current_unsigned_distance_m":float((root-fixed).length),
            "world_fixed_offset_drift_m":float(((root-fixed)-offset).length)})
output={"schema":"equine.pony.original_body_follicle_projection_48f.v1",
    "source_blend_sha256":capsule["source_blend_sha256"],
    "source_capsule_sha256":contract["source_capsule_sha256"],
    "source_kind":"original_synthetic",
    "rig":"PonyRig30","source_original_body_mesh_count":len(objects),
    "source_mesh_names":source_names,"frame_count":48,"guide_count":6,
    "cards":[dict(record,rest_anchor=anchors[record["card_id"]]) for record in records],
    "body_closed_volume_validated":False,
    "nearest_geometry_is_signed_inside_outside":False,
    "original_source_roots_snapped":False,
    "projection_admitted_as_animated_follicle":False,
    "visual_scientific_hold":"KEEP","release_or_CPE_admission":False}
out.write_text(json.dumps(output,sort_keys=True,indent=2)+"\n")
print("SCP_ORIGINAL_PONY_BODY_FOLLICLE_BARYCENTRIC_48F",json.dumps({
    "rest_anchors":[{"id":c["card_id"],"region":c["region"],
                     "object":c["rest_anchor"]["source_body_object"],
                     "dist_m":round(c["rest_anchor"]["rest_root_to_skin_distance_m"],6)}
                    for c in output["cards"]],
    "max_unsigned_nearest_m":max(s["nearest_unsigned_distance_m"] for c in output["cards"] for s in c["frames"]),
    "max_rest_face_tracking_m":max(s["world_fixed_offset_drift_m"] for c in output["cards"] for s in c["frames"]),
    "science":"KEEP","release_or_CPE":False},sort_keys=True))
