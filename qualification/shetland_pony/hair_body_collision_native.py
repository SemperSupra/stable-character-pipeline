#!/usr/bin/env python3
"""Read-only 48-frame native hair-card vs exact evaluated body triangle screen.

All 1050 source-authored longhair cards, all original 48 animation poses.
Exclude only follicle/root-to-first-quarter ribbon faces; analyze lower 75%
card triangles, plus distal tip distances. Real BVH triangle *crossings* and
unsigned proximity are useful falsifiers, not signed-solid containment,
contact pressure, veterinary anatomy, short-coat contact or hair realism.
"""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
from curved_groom import VERTS_PER_CARD
from hair_contact_quality import classify,REGION_CARDS,OBSTACLES

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=2:
    raise SystemExit("usage: blender -b --python hair_body_collision_native.py -- <source.blend> <report.json>")
source,out=map(Path,sys.argv[sys.argv.index("--")+1:])
if not source.is_file() or out.exists():
    raise ValueError("missing source or refuse overwriting prior science evidence")
if not 1024<=source.stat().st_size<=300_000_000:
    raise ValueError("source does not meet byte bounds")
out.parent.mkdir(parents=True,exist_ok=True)

def make_bvh(points,triangles):
    if not points or not triangles:
        raise ValueError("empty measured triangle surface")
    if any(len(face)!=3 or any(type(i) is not int or i<0 or i>=len(points) for i in face)
           for face in triangles):
        raise ValueError("invalid triangle index")
    if any(not math.isfinite(q) for p in points for q in p):
        raise ValueError("nonfinite evaluated triangle")
    return BVHTree.FromPolygons([Vector(x) for x in points],triangles,all_triangles=True,epsilon=.000001)

def positive_negative_controls():
    source=make_bvh(((0,0,0),(1,0,0),(0,1,0)),[(0,1,2)])
    crossing=make_bvh(((.25,.25,-.5),(.25,.25,.5),(.75,.25,0)),[(0,1,2)])
    separated=make_bvh(((10,0,0),(11,0,0),(10,1,0)),[(0,1,2)])
    if not source.overlap(crossing) or source.overlap(separated):
        raise ValueError("native Blender triangle intersection controls fail")

def evaluated_points_and_triangles(obj,dg):
    e=obj.evaluated_get(dg)
    mesh=e.to_mesh()
    try:
        if mesh is None or len(mesh.vertices)<3 or len(mesh.polygons)<1:
            raise ValueError("empty evaluated geometry "+obj.name)
        transform=e.matrix_world.copy()
        pts=[tuple(transform@v.co) for v in mesh.vertices]
        tris=[tuple(p.vertices) for p in mesh.polygons]
        return pts,tris
    finally:
        e.to_mesh_clear()

positive_negative_controls()
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
scene=bpy.context.scene
groom=bpy.data.objects.get("geometric_coat_mane_tail")
if groom is None or groom.type!="MESH":
    raise ValueError("missing original longhair surface")
if any(bpy.data.objects.get(name) is None or bpy.data.objects[name].type!="MESH"
       for targets in OBSTACLES.values() for name in targets):
    raise ValueError("missing original source body collision surface")

limits={"mane":(0,440),"forelock":(440,670),"tail":(670,1050)}
if any(b-a!=REGION_CARDS[name] for name,(a,b) in limits.items()):
    raise ValueError("source card partition drift")
rows=[];states={r:set() for r in limits};all_faces_count=None
for frame in range(1,49):
    scene.frame_set(frame)
    dg=bpy.context.evaluated_depsgraph_get()
    points,faces=evaluated_points_and_triangles(groom,dg)
    if len(points)!=1050*VERTS_PER_CARD or len(faces)!=1050*8:
        raise ValueError("changed longhair card topology in evaluated scene")
    region_faces={r:[] for r in limits}
    face_to_card={r:[] for r in limits}
    for face in faces:
        card=face[0]//VERTS_PER_CARD
        if card<0 or card>=1050 or any(i//VERTS_PER_CARD!=card for i in face):
            raise ValueError("cross-card or out-of-bounds source triangle")
        # Omit precisely the initial skin-anchored face row; do NOT ignore
        # distal hair crossing body or limb triangle surfaces.
        if min((i%VERTS_PER_CARD)//2 for i in face)==0:continue
        r="mane" if card<440 else "forelock" if card<670 else "tail"
        region_faces[r].append(face)
        face_to_card[r].append(card)
    if sum(len(v) for v in region_faces.values())!=6300:
        raise ValueError("unexpected distal 75pct card polygon count")
    region_bvhs={r:make_bvh(points,region_faces[r]) for r in limits}
    for region,(first,stop) in limits.items():
        digest=hashlib.sha256()
        for card in range(first,stop, max(1,(stop-first)//17)):
            a=card*VERTS_PER_CARD
            p=tuple((points[a+VERTS_PER_CARD-2][k]+points[a+VERTS_PER_CARD-1][k])*.5
                    for k in range(3))
            digest.update("|".join(str(round(q*1000)) for q in p).encode())
        states[region].add(digest.hexdigest())
        for name in OBSTACLES[region]:
            target_points,target_faces=evaluated_points_and_triangles(bpy.data.objects[name],dg)
            collider=make_bvh(target_points,target_faces)
            crossings=region_bvhs[region].overlap(collider)
            touched={face_to_card[region][h] for h,_ in crossings}
            distances=[]
            for card in range(first,stop):
                a=card*VERTS_PER_CARD
                tip=Vector(tuple((points[a+VERTS_PER_CARD-2][k]+points[a+VERTS_PER_CARD-1][k])*.5
                      for k in range(3)))
                location,normal,index,distance=collider.find_nearest(tip)
                if location is None or normal is None or not math.isfinite(distance):
                    raise ValueError("unresolved native tip proximity "+name)
                distances.append(distance)
            rows.append({"frame":frame,"region":region,"obstacle":name,
                         "face_pairs":len(crossings),"card_count":len(touched),
                         "tip_samples":stop-first,
                         "tips_within_5mm":sum(d<.005 for d in distances),
                         "min_tip_distance_m":min(distances)})
    if frame in (1,12,24,36,48):
        print("EQUINE_HAIR_BODY_NATIVE_POSE",frame,"measured_targets",sum(len(x) for x in OBSTACLES.values()))
result=classify(rows)
result.update({"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
               "engine":"Blender 4.5 source-evaluated skin and native BVHTree, triangles",
               "frames_examined":48,
               "source_cards":1050,"triangles_distal_75pct_per_frame":6300,
               "tip_sample_definition":"centroid of two final strand vertices per card",
               "deliberate_exclusion":"follicle first 25pct of each long-hair card only",
               "unique_tip_state_signatures_per_region":{r:len(states[r]) for r in limits},
               "validation_controls":"1 positive crossing, 1 far negative; source cardinalities and 48f complete",
               "collision_not_tested":"internal containment, winter fur, fabric/tack, continuous swept volume",
               "scientific_hold":"KEEP"})
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("EQUINE_HAIR_BODY_48F_CONTACT_SCIENCE_HOLD",
      result["candidate_collision"],
      json.dumps({r:{o:a["hair_card_frame_observations"] for o,a in v["obstacle_contacts"].items()}
                   for r,v in result["regions"].items()},sort_keys=True))
