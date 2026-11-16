"""R036 original, minimal Blender anatomy-binding vertical slice.
Loads one explicitly pinned CC0 MPFB hm08 base OBJ; all diagnostic anatomy, bindings,
animation, colors and validation code here are original. NOT a clinically accurate
skeleton, rig, organ set, photorealism test or production MakeHuman rig.
"""
import bpy
import argparse
import hashlib
import json
import math
import os
import struct
import sys
from mathutils import Vector

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase",choices=["build","verify"],required=True)
    parser.add_argument("--base",default="")
    parser.add_argument("--output",required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])

def report(data):
    print("R036_RECEIPT "+json.dumps(data,sort_keys=True))

def stop(reason):
    report({"status":"FAIL","reason":reason})
    raise RuntimeError(reason)

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def material(name,color,alpha=1.0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,alpha)
    m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(*color,1)
    bsdf.inputs["Roughness"].default_value=0.66
    return m

def viewport_vertex_digest(obj):
    bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get()
    evaluated=obj.evaluated_get(graph)
    mesh=evaluated.to_mesh()
    try:
        h=hashlib.sha256()
        for v in mesh.vertices:
            co=evaluated.matrix_world @ v.co
            h.update(struct.pack("<3f",*co))
        return h.hexdigest(),len(mesh.vertices)
    finally:evaluated.to_mesh_clear()

def scene_setup(filepath):
    if not filepath or not os.path.isfile(filepath):stop("missing authorized pinned MPFB base.obj")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.obj_import(filepath=filepath)
    meshobjects=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    if not meshobjects:stop("OBJ did not yield any mesh")
    body=max(meshobjects,key=lambda o:len(o.data.vertices))
    if len(body.data.vertices)<1000:stop("not a MakeHuman-scale mesh")
    for obj in meshobjects:
        if obj!=body:bpy.data.objects.remove(obj,do_unlink=True)
    body.name="MPFB_hm08_CC0_Body_Diagnostic"
    bpy.context.view_layer.objects.active=body
    body.select_set(True)
    for o in bpy.context.selected_objects:
        if o!=body:o.select_set(False)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    xyz=list(zip(*[v.co[:] for v in body.data.vertices]))
    ranges=[max(a)-min(a) for a in xyz]
    tall=max(range(3),key=lambda i:ranges[i])
    if tall==1:
        body.rotation_euler[0]=math.pi/2
    elif tall==0:
        body.rotation_euler[1]=-math.pi/2
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    xyz=list(zip(*[v.co[:] for v in body.data.vertices]))
    mins=[min(x) for x in xyz]
    maxs=[max(x) for x in xyz]
    h=maxs[2]-mins[2]
    if h<=0.01:stop("implausible body mesh vertical extent")
    center=Vector(((maxs[0]+mins[0])/2,(maxs[1]+mins[1])/2,0))
    z0=mins[2]
    # Diagnostic approximate two-bone spine. Not a MakeHuman anatomical rig.
    armdata=bpy.data.armatures.new("R036_Diagnostic_Armature")
    rig=bpy.data.objects.new("R036_Diagnostic_ControlRig",armdata)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    root=armdata.edit_bones.new("R036_Root")
    root.head=(center.x,center.y,z0+.02*h)
    root.tail=(center.x,center.y,z0+.47*h)
    torso=armdata.edit_bones.new("R036_Torso")
    torso.head=(center.x,center.y,z0+.47*h)
    torso.tail=(center.x,center.y,z0+.85*h)
    torso.parent=root
    torso.use_connect=True
    bpy.ops.object.mode_set(mode="OBJECT")
    body.vertex_groups.clear()
    rootgrp=body.vertex_groups.new(name="R036_Root")
    topgrp=body.vertex_groups.new(name="R036_Torso")
    for v in body.data.vertices:
        relative=(v.co.z-z0)/h
        w=max(0.0,min(1.0,(relative-.33)/.45))
        if w<1.0:rootgrp.add([v.index],1-w,"REPLACE")
        if w>0.0:topgrp.add([v.index],w,"REPLACE")
    body.parent=rig
    modifier=body.modifiers.new("R036_Armature_Deform","ARMATURE")
    modifier.object=rig
    body.data.materials.clear()
    body.data.materials.append(material("R036_Diagnostic_Skin",(0.55,0.37,0.29)))
    body["anatomical_truth"]="UNVALIDATED"
    body["source"]="MPFB hm08 raw base OBJ; source hash in external receipt"
    body["binding"]="two original diagnostic bones, procedural vertex weights"

    def add_organ(name,xoffset,zfraction,radius,color):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=(center.x+xoffset*h,center.y,z0+zfraction*h))
        obj=bpy.context.object
        obj.name=name
        obj.scale=(radius*h*.63,radius*h*.38,radius*h)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        obj.data.materials.append(material(name+"_mat",color))
        group=obj.vertex_groups.new(name="R036_Torso")
        group.add(list(range(len(obj.data.vertices))),1,"REPLACE")
        obj.parent=rig
        mod=obj.modifiers.new("R036_Follows_Armature","ARMATURE")
        mod.object=rig
        obj["anatomical_truth"]="SYNTHETIC_PROXY_NOT_MEDICAL"
        return obj

    lungL=add_organ("R036_LeftLung_Proxy",-.08,.68,.09,(.70,.31,.35))
    lungR=add_organ("R036_RightLung_Proxy",.08,.68,.09,(.70,.31,.35))
    diaphragm=add_organ("R036_Diaphragm_Proxy",0,.57,.035,(.36,.52,.70))
    diaphragm.scale.x*=3
    diaphragm.scale.y*=1.75

    torso_p=rig.pose.bones["R036_Torso"]
    torso_p.rotation_mode="XYZ"
    for frame,angle in [(1,0),(12,.11),(24,.18)]:
        torso_p.rotation_euler=(angle,0,0)
        torso_p.keyframe_insert(data_path="rotation_euler",frame=frame)
    scene=bpy.context.scene
    scene.frame_start=1
    scene.frame_end=24
    scene.render.engine="CYCLES"
    scene.cycles.samples=8
    scene.cycles.device="CPU"
    scene.render.resolution_x=256
    scene.render.resolution_y=256
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.world.color=(.12,.12,.12)
    bpy.ops.object.camera_add(location=(center.x+1.3*h,center.y-2*h,z0+.64*h))
    camera=bpy.context.object
    target=Vector((center.x,center.y,z0+.54*h))
    camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.camera=camera
    bpy.ops.object.light_add(type="AREA",location=(center.x+.9*h,center.y-.9*h,z0+1.2*h))
    light=bpy.context.object
    light.data.energy=1000
    light.data.shape="DISK"
    light.data.size=h
    return body,rig,[lungL,lungR,diaphragm],h

def run_build(ns):
    os.makedirs(ns.output,exist_ok=True)
    body,rig,organs,h=scene_setup(ns.base)
    scene=bpy.context.scene
    scene.frame_set(1)
    first_body,n=viewport_vertex_digest(body)
    first_organ,_=viewport_vertex_digest(organs[0])
    body.hide_render=False
    for organ in organs:organ.hide_render=True
    scene.render.filepath=os.path.join(ns.output,"surface_frame01.png")
    bpy.ops.render.render(write_still=True)
    scene.frame_set(24)
    posed_body,n2=viewport_vertex_digest(body)
    posed_organ,_=viewport_vertex_digest(organs[0])
    if n!=n2 or first_body==posed_body or first_organ==posed_organ:
        stop("missing real skin or attached internal organ deformation")
    # Rendering isolation: toggling visible anatomy may not perturb evaluated body.
    before,_=viewport_vertex_digest(body)
    for organ in organs:organ.hide_render=False
    after,_=viewport_vertex_digest(body)
    if before!=after:stop("visibility changed evaluated external deformation")
    body.hide_render=True
    scene.render.filepath=os.path.join(ns.output,"anatomy_frame24.png")
    bpy.ops.render.render(write_still=True)
    body.hide_render=False
    for organ in organs:organ.hide_render=True
    scene.render.filepath=os.path.join(ns.output,"surface_frame24.png")
    bpy.ops.render.render(write_still=True)
    blendpath=os.path.join(ns.output,"mpfb-anatomy-diagnostic.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blendpath,check_existing=False)
    # Export both canonical skin and named interior structures, preserving skinning
    # only when exporter represents it. Verify GLB has both skeleton+skin.
    for o in bpy.context.selected_objects:o.select_set(False)
    body.select_set(True)
    rig.select_set(True)
    for obj in organs:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    glbpath=os.path.join(ns.output,"mpfb-anatomy-diagnostic.glb")
    bpy.ops.export_scene.gltf(filepath=glbpath,export_format="GLB",use_selection=True)
    record={
      "status":"PASS_NATIVE_SMOKE",
      "scope":"CC0_MPFB_BASE_DERIVED_WITH_SYNTHETIC_TWO_BONE_RIG_AND_ORGAN_PROXIES_ONLY",
      "source_base_sha256":sha(ns.base),"blender":bpy.app.version_string,
      "body_vertices":n,"body_vertex_count_unchanged":n==n2,
      "body_digest_rest":first_body,"body_digest_pose":posed_body,
      "organ_digest_rest":first_organ,"organ_digest_pose":posed_organ,
      "hide_render_does_not_change_body":before==after,
      "scene_sha256":sha(blendpath),"glb_sha256":sha(glbpath),
      "images":{os.path.basename(p):sha(os.path.join(ns.output,p)) for p in ("surface_frame01.png","surface_frame24.png","anatomy_frame24.png")},
      "caveats":["not original MPFB native rig","not anatomically located organs","not physical tissue or muscle simulation","not photorealism","not full MakeHuman/MPFB addon integration"]
    }
    with open(os.path.join(ns.output,"receipt.json"),"w") as f:json.dump(record,f,indent=2,sort_keys=True)
    report(record)

def run_verify(ns):
    body=bpy.data.objects.get("MPFB_hm08_CC0_Body_Diagnostic")
    rig=bpy.data.objects.get("R036_Diagnostic_ControlRig")
    if body is None or rig is None or body.type!="MESH" or rig.type!="ARMATURE":stop("reloaded scene lost MakeHuman body or rig")
    if not any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers):stop("reloaded character lost skinning rig binding")
    organ=bpy.data.objects.get("R036_LeftLung_Proxy")
    if organ is None or not any(m.type=="ARMATURE" and m.object==rig for m in organ.modifiers):stop("reloaded scene lost organ binding")
    bpy.context.scene.frame_set(1)
    b1,n=viewport_vertex_digest(body)
    o1,_=viewport_vertex_digest(organ)
    bpy.context.scene.frame_set(24)
    b2,n2=viewport_vertex_digest(body)
    o2,_=viewport_vertex_digest(organ)
    if b1==b2 or o1==o2 or n!=n2:stop("reopened scene motion did not change geometry")
    glb=os.path.join(ns.output,"mpfb-anatomy-diagnostic.glb")
    with open(glb,"rb") as f:
        header=f.read(12)
        if len(header)!=12 or header[:4]!=b"glTF":stop("GLB magic mismatch")
        length,chunk_type=struct.unpack("<II",f.read(8))
        if chunk_type!=0x4e4f534a:stop("GLB missing JSON chunk")
        doc=json.loads(f.read(length))
    if not doc.get("skins") or len(doc.get("meshes",[]))<2:stop("glTF did not retain at least one skin and two meshes")
    report({"status":"PASS_REOPEN_AND_INTERCHANGE_SMOKE","blender":bpy.app.version_string,
      "body_vertices":n,"reopened_motion_preserved":True,
      "organ_binding_preserved":True,"gltf_skins":len(doc["skins"]),
      "gltf_meshes":len(doc["meshes"]),"glb_sha256":sha(glb),
      "limits":"not an independent renderer/game-engine import or physiology validation"})

if __name__=="__main__":
    ns=args()
    if ns.phase=="build":run_build(ns)
    else:run_verify(ns)
