#!/usr/bin/env python3
"""R072: actual Blender two-bone Armature modifier, source-known LBS, Cycles EXR.

All geometry/materials are made from original procedural primitives on a free
public CPU runner. Not a real person, MakeHuman rig, native animation or gait.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"renderlab"))
sys.path.insert(0,str(ROOT/"perspprobe"))
import synthetic_scene as base
import scene as perspective

ANGLE={0:0.0,1:0.34,2:-0.29}
SIDES=12
RINGS=8
RIG_NAME="r072-original-two-bone-armature"
MESH_NAME="r072-original-weighted-sleeve"
BONES=("root","tip")

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def flattened(m):
    return [round(float(v),9) for row in m for v in row]

def construct_rig(scene):
    vertices=[]
    faces=[]
    weights=[]
    # A source-original conspicuous segmented sleeve standing in front of the
    # stylized head. This is NOT native tissue or a MakeHuman mesh.
    for row in range(RINGS):
        z=1.00 + 0.19*row
        wt=min(1.0,max(0.0,(z-1.34)/0.84))
        for k in range(SIDES):
            angle=2*math.pi*k/SIDES
            vertices.append((0.285*math.cos(angle),
                             -0.87+0.285*math.sin(angle),z))
            weights.append([round(1-wt,9),round(wt,9)])
    for row in range(RINGS-1):
        for k in range(SIDES):
            a=row*SIDES+k
            b=row*SIDES+(k+1)%SIDES
            faces.append((a,b,b+SIDES,a+SIDES))
    faces.append(tuple(reversed(tuple(range(SIDES)))))
    faces.append(tuple((RINGS-1)*SIDES+k for k in range(SIDES)))
    mesh=bpy.data.meshes.new(MESH_NAME+"-rest")
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    obj=bpy.data.objects.new(MESH_NAME,mesh)
    scene.collection.objects.link(obj)
    obj.pass_index=3
    obj.data.materials.append(base.material(
        "r072-original-green-skin-probe",(0.09,0.46,0.16),"baseline"))
    for poly in mesh.polygons:
        poly.use_smooth=True

    arm_data=bpy.data.armatures.new(RIG_NAME+"-data")
    arm=bpy.data.objects.new(RIG_NAME,arm_data)
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    root=arm_data.edit_bones.new("root")
    root.head=(0,-0.87,0.9)
    root.tail=(0,-0.87,1.62)
    tip=arm_data.edit_bones.new("tip")
    tip.head=(0,-0.87,1.62)
    tip.tail=(0,-0.87,2.45)
    tip.parent=root
    tip.use_connect=True
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.select_set(False)
    for name in BONES:
        obj.vertex_groups.new(name=name)
    for i,(w0,w1) in enumerate(weights):
        if w0>0:obj.vertex_groups["root"].add([i],w0,"REPLACE")
        if w1>0:obj.vertex_groups["tip"].add([i],w1,"REPLACE")
    modifier=obj.modifiers.new("r072-actual-armature-deform","ARMATURE")
    modifier.object=arm
    modifier.use_vertex_groups=True
    modifier.use_deform_preserve_volume=False
    bpy.context.view_layer.update()
    if obj.matrix_world!=Matrix.Identity(4) or arm.matrix_world!=Matrix.Identity(4):
        raise RuntimeError("R072_EXPECTED_IDENTITY_LOCAL_WORLD_BIND")
    source={"vertex_bind":vertices,"weights":weights,
            "faces":[list(f) for f in faces],"bone_names":list(BONES),
            "bone_rest_matrices":{name:flattened(arm_data.bones[name].matrix_local)
                                  for name in BONES},
            "rest_mesh_sha256":base.canonical_hash({
                "vertices":vertices,"faces":faces,"weights":weights
            })}
    return obj,arm,source

def evaluated_mesh_and_bones(obj,arm):
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    evaluated=obj.evaluated_get(dg)
    tmp=evaluated.to_mesh()
    if tmp is None:raise RuntimeError("R072_MISSING_EVALUATED_MESH")
    try:
        vertices=[[round(float(v),9) for v in evaluated.matrix_world @ p.co]
                  for p in tmp.vertices]
        faces=[list(p.vertices) for p in tmp.polygons]
    finally:
        evaluated.to_mesh_clear()
    matrices={}
    for name in BONES:
        bone=arm.data.bones[name]
        pose=arm.pose.bones[name]
        transform=pose.matrix @ bone.matrix_local.inverted()
        matrices[name]=flattened(transform)
    return vertices,faces,matrices

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    scene=base.make_scene("baseline")
    cam=scene.camera
    cam.data.type="PERSP"
    cam.data.sensor_fit="HORIZONTAL"
    cam.data.sensor_width=36.0
    cam.data.lens=65.0
    cam.data.shift_x=0.0
    cam.data.shift_y=0.0
    bpy.context.view_layer.update()
    camera=perspective.camera_record(scene)
    mesh,arm,source=construct_rig(scene)
    original_source_script=sha(ROOT/"renderlab"/"synthetic_scene.py")
    frame_data={}
    for frame,angle in sorted(ANGLE.items()):
        scene.frame_set(frame)
        for bone in arm.pose.bones:
            bone.rotation_mode="XYZ"
            bone.rotation_euler=(0.0,0.0,0.0)
        arm.pose.bones["tip"].rotation_euler[0]=angle
        bpy.context.view_layer.update()
        if perspective.camera_record(scene)!=camera:
            raise RuntimeError("R072_UNEXPECTED_CAMERA_MOTION")
        vertices,faces,transforms=evaluated_mesh_and_bones(mesh,arm)
        if faces!=source["faces"] or len(vertices)!=len(source["vertex_bind"]):
            raise RuntimeError("R072_TOPOLOGY_OR_VERTEX_COUNT_CHANGED")
        rays,n=perspective.rays_for(scene)
        instrumented=sum(r["stable"] and r["pass_index"]==3 for r in rays)
        if instrumented<2:raise RuntimeError("R072_WEIGHTED_MESH_NOT_VISIBLE_IN_RAYS")
        target=out/("frame_%02d"%frame)
        target.mkdir(parents=True,exist_ok=True)
        files={}
        for filename,fmt in (("beauty.png","PNG"),("render_passes.exr","OPEN_EXR_MULTILAYER")):
            scene.render.image_settings.file_format=fmt
            scene.render.filepath=str(target/filename)
            bpy.ops.render.render(write_still=True)
            path=target/filename
            if not path.exists() or path.stat().st_size<128:
                raise RuntimeError("R072_REAL_CYCLES_RENDER_NOT_CREATED")
            files[filename]={"sha256":sha(path),"bytes":path.stat().st_size}
        frame_data[str(frame)]={
            "frame_index":frame,"tip_local_rotation_x_radians":angle,
            "armature_pose_matrices":transforms,
            "evaluated_vertices":vertices,
            "evaluated_mesh_sha256":base.canonical_hash({
                "vertices":vertices,"faces":faces
            }),
            "rays":rays,"stable_ray_count":n,
            "stable_rig_ray_count":instrumented,
            "camera_sha256":base.canonical_hash(camera),
            "files":files,
        }
        print("R072_ACTUAL_BONED_CYCLES_FRAME",frame,"rays",n,
              "rig_rays",instrumented,"verts",len(vertices),flush=True)
    if len({f["evaluated_mesh_sha256"] for f in frame_data.values()})!=3:
        raise RuntimeError("R072_SOURCE_RIG_DID_NOT_DEFORM")
    report={
        "schema":"r072.synthetic.skinning.native.v1",
        "status":"NATIVE_ARMATURE_SOURCE_CAPTURE_PENDING_INDEPENDENT_LBS_EXR",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_REAL_PERSON_OR_MAKEHUMAN_SKINNING",
        "source_scene_id":base.SCENE_ID,
        "original_source_script_sha256":original_source_script,
        "perspective_script_sha256":sha(ROOT/"perspprobe"/"scene.py"),
        "camera":camera,
        "camera_sha256":base.canonical_hash(camera),
        "rig_object_name":MESH_NAME,
        "rig_object_id":3,
        "motion_type":"TWO_BONE_LINEAR_BLEND_SKINNING_NO_HUMAN",
        "source":source,
        "frames":frame_data,
    }
    (out/"r072_source.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("R072_REAL_EVALUATED_ARMATURE_AND_EXR_CAPTURED",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    run(args.out)
