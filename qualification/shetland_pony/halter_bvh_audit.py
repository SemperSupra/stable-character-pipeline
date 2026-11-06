#!/usr/bin/env python3
"""Independent native evaluated 5-frame head/halter nearest-triangle screen.

This audits real skinned geometry against original synthetic equine head.
Signed nearest-face normal is a local screening signal, NOT a true signed
distance field, closed-volume inside test, veterinary tack fit certification,
or dynamic contact solver. Scientific warnings never become green CI proofs.
"""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import hashlib
import json
import math
import sys
from pathlib import Path

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=2:
    raise SystemExit("usage: blender -b --python halter_bvh_audit.py -- <joined.blend> <report.json>")
source,report=map(Path,sys.argv[sys.argv.index("--")+1:])
if not source.is_file():raise FileNotFoundError(source)
report.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
scene=bpy.context.scene
head=bpy.data.objects.get("sculpt_equine_brow_bridge_muzzle")
parts=("halter_cheek_L","halter_cheek_R","halter_crownpiece",
       "halter_noseband","halter_throatlatch")
if head is None or head.type!="MESH":raise ValueError("head source missing")
if any(bpy.data.objects.get(n) is None for n in parts):
    raise ValueError("incomplete five-strap halter")
frames=(1,10,24,40,48)
result={"schema":"equine.halter.evaluated_bvh_screen.v1",
        "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "scoping":"actual evaluated head+strap meshes in head-local coordinates; 5 selected source poses",
        "limitations":"nearest-triangle normal is not exact signed distance or watertight collision certification; no fur/tack hardware friction or veterinary assessment",
        "science_hold":"KEEP, regardless of any numerical engineering CI pass",
        "frames":{}}
for frame in frames:
    scene.frame_set(frame)
    dg=bpy.context.evaluated_depsgraph_get()
    h=head.evaluated_get(dg)
    hm=h.to_mesh()
    if hm is None or len(hm.vertices)<500 or len(hm.polygons)<1000:
        raise ValueError("invalid evaluated source head topology")
    vertices=[v.co.copy() for v in hm.vertices]
    polygons=[tuple(p.vertices) for p in hm.polygons]
    bvh=BVHTree.FromPolygons(vertices,polygons,all_triangles=False)
    head_inv=h.matrix_world.inverted_safe()
    row={}
    for part in parts:
        obj=bpy.data.objects[part].evaluated_get(dg)
        mesh=obj.to_mesh()
        if mesh is None or len(mesh.vertices)<12:
            raise ValueError("missing evaluated strap surface "+part)
        tx=head_inv@obj.matrix_world
        signed=[];distances=[]
        for vertex in mesh.vertices:
            p=tx@vertex.co
            location,normal,index,distance=bvh.find_nearest(p)
            if location is None or normal is None or not math.isfinite(distance):
                raise ValueError("no nearest triangle evidence "+part)
            side=(p-location).dot(normal)
            if not math.isfinite(side):raise ValueError("nonfinite normal side")
            signed.append(side)
            distances.append(distance)
        obj.to_mesh_clear()
        n=len(signed)
        penetration=sum(s<-.002 for s in signed)
        near=sum(abs(s)<.004 for s in signed)
        row[part]={"vertices":n,"possible_penetrating_vertices":penetration,
                   "fraction_possible_penetration":round(penetration/n,5),
                   "near_surface_within_4mm":near,
                   "min_nearest_face_signed_m":round(min(signed),6),
                   "min_unsigned_head_distance_m":round(min(distances),6),
                   "max_unsigned_head_distance_m":round(max(distances),6)}
    h.to_mesh_clear()
    result["frames"][str(frame)]=row
result["any_potential_intersection"]=any(r["possible_penetrating_vertices"]>0
       for frame in result["frames"].values() for r in frame.values())
report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("HALTER_EVALUATED_BVH_SCIENCE_SCREEN",result["any_potential_intersection"],
      json.dumps({f:{p:v["possible_penetrating_vertices"] for p,v in r.items()}
                  for f,r in result["frames"].items()},sort_keys=True))
