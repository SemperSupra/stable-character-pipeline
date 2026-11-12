"""R014 deterministic first-pass surface/weight transfer, research only.

Source: corrected adult MPFB Blender rig (source gender schema validated),
target: official CC0 Blender Studio realistic sculpt base.
Methods: axis-aligned bounding box scale and optional facing reversal followed by
closest triangle barycentric up-to-4 skin weight transfer. The *receipt*, not
a visual aesthetic judgment, describes correspondence coverage, bone influences
and actual posed surface displacement.

This is a research bakeoff, not an anatomically accurate rig retarget.
"""
import argparse, json, math, sys
from pathlib import Path
from collections import defaultdict
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import numpy as np

p=argparse.ArgumentParser()
p.add_argument("--mpfb",required=True,type=Path)
p.add_argument("--studio",required=True,type=Path)
p.add_argument("--sex",choices=["female","male"],required=True)
p.add_argument("--generation",required=True,type=Path)
p.add_argument("--out",required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
generation=json.loads(a.generation.read_text())
assert {(x["sex"],x["source_gender_macro"]) for x in generation["characters"]}=={
    ("female",0.0),("male",1.0)
},"MPFB source phenotype macro invalid/reversed"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
with bpy.data.libraries.load(str(a.mpfb),link=False) as (src,dst):
    names=[n for n in src.objects if n.startswith("R014_"+a.sex+"_")]
    assert "R014_"+a.sex+"_body_clean_export" in names,names
    dst.objects=names
for obj in dst.objects:
    if obj is not None and obj.name not in bpy.context.collection.objects:
        bpy.context.collection.objects.link(obj)
mpfb=bpy.data.objects["R014_"+a.sex+"_body_clean_export"]
rigs=[m.object for m in mpfb.modifiers if m.type=="ARMATURE" and m.object]
assert len(rigs)==1,"one source rig required"
rig=rigs[0]
with bpy.data.libraries.load(str(a.studio),link=False) as (src,dst):
    name="GEO-body_"+a.sex+"_realistic"
    assert name in src.objects,"missing vetted sculpt body"
    dst.objects=[name]
sculpt=dst.objects[0]
bpy.context.collection.objects.link(sculpt)
assert len(mpfb.data.vertices)==13380 and len(sculpt.data.vertices)==10582, ("source is cleaned helper-free MPFB",len(mpfb.data.vertices),len(sculpt.data.vertices))
sculpt.data=sculpt.data.copy()
for m in sculpt.modifiers:
    if m.type=="MULTIRES":m.show_viewport=False;m.show_render=False

# Object world mesh coordinates, preserving untouched original .blend in Drive.
src=[mpfb.matrix_world@v.co for v in mpfb.data.vertices]
tgt=[sculpt.matrix_world@v.co for v in sculpt.data.vertices]
def centroid_extent(points):
    arr=np.array([list(v) for v in points],dtype=np.float64)
    lo=arr.min(axis=0);hi=arr.max(axis=0)
    return (lo+hi)/2,hi-lo
src_center,src_size=centroid_extent(src)
tgt_center,tgt_size=centroid_extent(tgt)
assert all(v>.08 for v in src_size) and all(v>.08 for v in tgt_size),"invalid extent"
scale=src_size/tgt_size
assert all(.3<float(v)<3.0 for v in scale),"unrealistic size alignment required"
world_coords=np.array([list(v) for v in tgt],dtype=np.float64)
src_vertices=np.array([list(v) for v in src],dtype=np.float64)

mpfb.data.calc_loop_triangles()
tris=[tuple(int(v) for v in t.vertices) for t in mpfb.data.loop_triangles]
assert len(tris)>15000 and len(tris)<150000,("cleaned source triangle census",len(tris))
bvh=BVHTree.FromPolygons([Vector(v) for v in src_vertices],tris,all_triangles=True)

def place(flip):
    arr=(world_coords-tgt_center)*scale
    if flip:arr[:,0]*=-1;arr[:,1]*=-1
    return arr+src_center

def sample_cost(positions):
    samples=positions[::max(1,len(positions)//350)]
    distances=[]
    for pos in samples:
        hit=bvh.find_nearest(Vector(pos))
        if hit[0] is None:raise ValueError("no source triangles")
        distances.append(hit[3])
    return float(np.percentile(distances,95))
candidate=[(sample_cost(place(flip)),flip) for flip in (False,True)]
cost,flip=min(candidate,key=lambda x:x[0])
aligned=place(flip)
inv=sculpt.matrix_world.inverted()
for idx,v in enumerate(sculpt.data.vertices):
    v.co=inv@Vector(aligned[idx].tolist())
bpy.context.view_layer.update()

def baryweights(pos,a,b,c):
    v0=b-a;v1=c-a;v2=pos-a
    d00=v0.dot(v0);d01=v0.dot(v1);d11=v1.dot(v1)
    d20=v2.dot(v0);d21=v2.dot(v1)
    denom=d00*d11-d01*d01
    if abs(denom)<1e-15:return (1.,0.,0.)
    w1=(d11*d20-d01*d21)/denom
    w2=(d00*d21-d01*d20)/denom
    w0=1.-w1-w2
    weights=[max(0.,min(1.,q)) for q in (w0,w1,w2)]
    s=sum(weights)
    return tuple(q/s for q in weights)

groups={g.index:g.name for g in mpfb.vertex_groups}
target_groups={name:sculpt.vertex_groups.new(name=name)
               for name in set(groups.values())}
source_weight=[{groups[x.group]:x.weight for x in v.groups if x.group in groups}
               for v in mpfb.data.vertices]
distances=[];influence_count=[];unweighted=0
for idx,pos in enumerate(aligned):
    hit,normal,triangle,dist=bvh.find_nearest(Vector(pos.tolist()))
    if hit is None:raise ValueError("source BVH correspondence lost")
    triangles=tris[triangle]
    ws=baryweights(hit,*[Vector(src_vertices[j].tolist()) for j in triangles])
    totals=defaultdict(float)
    for srcid,bary in zip(triangles,ws):
        for group,weight in source_weight[srcid].items():
            totals[group]+=bary*weight
    top=sorted(totals.items(),key=lambda x:-x[1])[:4]
    total=sum(v for _,v in top)
    if total<=1e-8:
        unweighted+=1
        continue
    for group,weight in top:
        if weight>1e-6:target_groups[group].add([idx],weight/total,"REPLACE")
    influence_count.append(len(top))
    distances.append(dist)
if unweighted:raise ValueError("unweighted sculpt vertices: "+str(unweighted))
assert len(distances)==len(sculpt.data.vertices)
assert 0<max(influence_count)<=4

arm=sculpt.modifiers.new("R014_Experimental_Transferred_MPFB_Rig","ARMATURE")
arm.object=rig
mpfb.hide_render=True
mpfb.hide_set(True)

scene=bpy.context.scene
def points():
    dg=bpy.context.evaluated_depsgraph_get()
    ev=sculpt.evaluated_get(dg)
    mesh=ev.to_mesh()
    try:
        return np.array([list(ev.matrix_world@v.co) for v in mesh.vertices],np.float64)
    finally:ev.to_mesh_clear()
scene.frame_set(1)
rest=points()
for name,rad in (("upperarm01.L",.32),("upperleg01.L",-.2)):
    assert name in rig.pose.bones,("source rig missing motion bone",name)
    bone=rig.pose.bones[name];bone.rotation_mode="XYZ"
    bone.rotation_euler[1]=rad
bpy.context.view_layer.update()
posed=points()
movement=np.linalg.norm(posed-rest,axis=1)
assert len(movement)==len(rest)
print("R014_POSE_DIAGNOSTIC",json.dumps({
    "sex":a.sex,"max_m":float(movement.max()),"p95_m":float(np.percentile(movement,95)),
    "all_nonzero":int(np.count_nonzero(movement>1e-6)),
    "rig_bones":len(rig.data.bones),
    "target_weight_groups":len(sculpt.vertex_groups),
    "source_rig_modifiers":[(m.type,m.object.name if m.type=="ARMATURE" and m.object else None) for m in mpfb.modifiers],
    "target_modifiers":[(m.type,m.object.name if m.type=="ARMATURE" and m.object else None) for m in sculpt.modifiers],
    "action":rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None
},sort_keys=True),flush=True)
assert movement.max()>.005,"source pose failed to actuate the sculpt"
pose_quality="HOLD_EXCESSIVE_DEFORMATION" if movement.max()>=.6 else "PASS_BOUND_TEST_ONLY"

# Render simple 2-panel technical silhouettes, no photoreal evidence.
mat=bpy.data.materials.new("R014_Clay_Sculpt_Transfer")
mat.diffuse_color=(.65,.62,.58,1)
sculpt.data.materials.clear()
sculpt.data.materials.append(mat)
scene.render.engine="CYCLES";scene.cycles.device="CPU"
scene.cycles.samples=8;scene.render.threads_mode="FIXED";scene.render.threads=4
scene.render.resolution_x=384;scene.render.resolution_y=512
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
world=bpy.data.worlds.new("R014_RigStudy_World");world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.9
scene.world=world
light=bpy.data.lights.new("R014_RigStudy_Key","AREA")
lamp=bpy.data.objects.new("R014_RigStudy_Key",light)
bpy.context.collection.objects.link(lamp)
light.energy=550;light.size=3
lamp.location=(float(src_center[0])+1.,-2.5,2.7)
cd=bpy.data.cameras.new("R014_RigStudy_Camera")
cam=bpy.data.objects.new("R014_RigStudy_Camera",cd)
bpy.context.collection.objects.link(cam);scene.camera=cam
cd.type="ORTHO"
# Use actual evaluated rest+pose vertex bounding boxes, not source mesh origin.
# The first attempted render produced mostly empty frames, correctly rejected
# during independent review despite large valid-looking PNG files.
from bpy_extras.object_utils import world_to_camera_view
both=np.vstack((rest,posed))
low=both.min(axis=0)
high=both.max(axis=0)
mid=(low+high)*.5
extent=high-low
assert np.all(np.isfinite(extent)) and max(extent)>1.0
aspect=scene.render.resolution_x/scene.render.resolution_y
cd.ortho_scale=max(float(extent[2])*1.22,float(extent[0])/aspect*1.22,2.1)
cam.location=(float(mid[0]),float(mid[1])-max(float(extent[1])*3,4.0),float(mid[2]))
cam.rotation_euler=(Vector(mid.tolist())-cam.location).to_track_quat("-Z","Y").to_euler()
lamp.location=(float(mid[0])+1.2,float(mid[1])-2.0,float(mid[2])+1.8)
# update evaluated camera matrix before projecting, otherwise world_to_camera_view
# may use the old identity transform and report the visible body behind camera.
bpy.context.view_layer.update()
camera_qa={}
for caption,arr in (("neutral",rest),("posed",posed)):
    # Every vertex must be in front of the camera and inside the viewport.
    frame=[world_to_camera_view(scene,cam,Vector(q.tolist())) for q in arr]
    xy=np.array([[p.x,p.y] for p in frame],dtype=np.float64)
    z=np.array([p.z for p in frame],dtype=np.float64)
    mins=xy.min(axis=0);maxs=xy.max(axis=0)
    camera_qa[caption]={"min":mins.tolist(),"max":maxs.tolist(),"depth_min":float(z.min())}
    assert np.all(mins>0) and np.all(maxs<1) and np.all(z>0),("camera clips sculpt",caption,camera_qa[caption])
    assert (maxs[0]-mins[0])>.12 and (maxs[1]-mins[1])>.15,("tiny subject",caption,camera_qa[caption])
print("R014_CAMERA_COVERAGE",json.dumps(camera_qa,sort_keys=True),flush=True)
scene.render.filepath=str(a.out/"rigged_pose.png")
bpy.ops.render.render(write_still=True)
assert Path(scene.render.filepath).stat().st_size>10000
for name in ("upperarm01.L","upperleg01.L"):rig.pose.bones[name].rotation_euler[1]=0
bpy.context.view_layer.update()
scene.render.filepath=str(a.out/"neutral.png")
bpy.ops.render.render(write_still=True)
assert Path(scene.render.filepath).stat().st_size>10000
native=a.out/("R014_"+a.sex+"_sculpt_weight_transfer_research.blend")
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>100000

distance=np.array(distances)
result={
 "status":"PASS_WEIGHT_TRANSFER_EVIDENCE_CAPTURED_POSE_UNQUALIFIED",
 "pose_quality_status":pose_quality,
 "sex_source_macro":0.0 if a.sex=="female" else 1.0,
 "source":"MPFB 2.0.18 corrected neutral rig from public run 43202169814",
 "target":"Blender Studio CC0 v1.4.1 sculpt from run 43212080935",
 "source_mesh_vertices":len(src),"target_mesh_vertices":len(tgt),
 "source_bones":len(rig.data.bones),
 "source_triangles":len(tris),
 "alignment":{"axis_scale":scale.tolist(),"facing_rotated_180_degrees":flip,
              "sample_p95_before_full_transfer_m":cost},
 "correspondence":{"mean_m":float(distance.mean()),
                   "p95_m":float(np.percentile(distance,95)),
                   "max_m":float(distance.max()),
                   "fraction_over_50mm":float(np.mean(distance>.05)),
                   "fraction_over_100mm":float(np.mean(distance>.10))},
 "rig_influences":{"max":max(influence_count),"unweighted_vertices":unweighted},
 "camera_coverage":camera_qa,
 "motion":{"max_actual_vertex_delta_m":float(movement.max()),
           "p95_actual_vertex_delta_m":float(np.percentile(movement,95))},
 "native_blend":native.name,
 "renders":["neutral.png","rigged_pose.png"],
 "independent_quality_status":"HOLD_UNREVIEWED",
 "limitations":["Bounding-box alignment is not anatomical landmark registration",
  "Nearest-triangle weight transfer can assign anatomically wrong bones",
  "No self-collision, surface foldover or anatomically meaningful joint acceptance",
  "No face blendshapes or mouth/lip motion transfer",
  "No sex-organ completeness, skin textures, realistic materials or full video qualification",
  "Human visual review and separate anatomical mesh correspondence required"]
}
(a.out/"rig_transfer_receipt.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("R014_SCULPT_RIG_TRANSFER",json.dumps({k:v for k,v in result.items() if k!="limitations"},sort_keys=True))
