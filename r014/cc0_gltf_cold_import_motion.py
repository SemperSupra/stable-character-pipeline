"""R014 independent cold-process GLB import/playback qualification of native CC0.
Runs in a fresh Blender process with only portable GLB; no original .blend
loaded or Python model runtime. Real skin deformation is measured on the
imported evaluated mesh and animation, not inferred from JSON channels alone.
"""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import struct
import sys
import bpy

def sha(path):
    h=sha256()
    with Path(path).open("rb") as f:
        for x in iter(lambda:f.read(1<<20),b""):h.update(x)
    return h.hexdigest()

def read_glb(path):
    with path.open("rb") as f:
        magic,version,length=struct.unpack("<4sII",f.read(12))
        assert magic==b"glTF" and version==2 and length==path.stat().st_size
        size,kind=struct.unpack("<I4s",f.read(8))
        assert kind==b"JSON"
        doc=json.loads(f.read(size))
    assert len(doc.get("skins",[]))>=1 and len(doc.get("animations",[]))>=1
    rot=[c for a in doc["animations"] for c in a["channels"]
         if c.get("target",{}).get("path")=="rotation"]
    assert len(rot)>=100,"GLB_ROTATION_CHANNELS_TOO_FEW"
    return {"skins":len(doc["skins"]),"animations":len(doc["animations"]),
            "meshes":len(doc["meshes"]),"rotation_channels":len(rot)}

def mesh_world_vertices(obj):
    dg=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(dg);mesh=ev.to_mesh()
    try:
        indices=sorted({int(i*(len(mesh.vertices)-1)/max(1,1023)) for i in range(1024)})
        return [[float(x) for x in ev.matrix_world@mesh.vertices[i].co] for i in indices]
    finally:ev.to_mesh_clear()

def max_delta(a,b):
    assert len(a)==len(b)
    return max(math.dist(p,q) for p,q in zip(a,b))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sex",choices=("female","male"),required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--author-receipt",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    args.out.mkdir(parents=True,exist_ok=True)
    assert bpy.data.filepath=="","NOT_A_FRESH_BLENDER_PROCESS"
    source=json.loads(args.author_receipt.read_text())
    assert source["sex_macro"]==args.sex
    assert source["status"]=="PASS_BOUNDED_REAL_SOURCE_NATIVE_TEMPORAL_EVIDENCE_CAPTURE_ONLY"
    assert source["glb"]["sha256"]==sha(args.source)
    assert source["glb"]["skins"]>=1 and source["glb"]["animations"]>=1
    original=read_glb(args.source)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.source))
    rigs=[obj for obj in bpy.data.objects if obj.type=="ARMATURE"]
    meshes=[obj for obj in bpy.data.objects if obj.type=="MESH"]
    assert rigs and len(meshes)>=6,("MISSING_IMPORTED_RIG_OR_MESH",len(rigs),len(meshes))
    rig=max(rigs,key=lambda x:len(x.data.bones))
    assert len(rig.data.bones)>=100
    skin=[obj for obj in meshes if any(m.type=="ARMATURE" and m.object==rig for m in obj.modifiers)]
    assert skin, "IMPORTED_GLTF_LOST_SKIN_LINKAGE"
    body=max(skin,key=lambda x:len(x.data.vertices))
    assert len(body.data.vertices)>=10000, "IMPORTED_SOURCE_BODY_TOO_SMALL"
    actions=sorted([(act.name,float(act.frame_range[0]),float(act.frame_range[1]))
                    for act in bpy.data.actions],key=lambda a:a[2]-a[1],reverse=True)
    assert actions, "NO_IMPORTED_PLAYABLE_ACTION"
    # glTF time is serialized in seconds; Blender importer may map the
    # original 12fps to a fresh scene's own FPS, so inspect imported action.
    first=math.floor(min(x[1] for x in actions))
    last=math.ceil(max(x[2] for x in actions))
    assert last-first>=10,("NO_TIMELINE_IMPORT",actions)
    middle=round((first+last)/2)
    scene=bpy.context.scene
    scene.frame_set(first)
    bpy.context.view_layer.update()
    a=mesh_world_vertices(body)
    scene.frame_set(middle)
    bpy.context.view_layer.update()
    b=mesh_world_vertices(body)
    scene.frame_set(last)
    bpy.context.view_layer.update()
    c=mesh_world_vertices(body)
    motion=max_delta(a,b)
    restoration=max_delta(a,c)
    # Numeric details always retained even when motion fails, to avoid
    # treating action/skin presence as equivalent to actually playable body.
    report={
        "schema":"r014.cc0.gltf_2_cold_blender_import_deformation.v1",
        "status":"INCOMPLETE",
        "source_sex_macro":args.sex,
        "source_exact_glb_sha256":sha(args.source),
        "original_glb":original,"original_author_source_run":43368839856,
        "import_blender_version":bpy.app.version_string,
        "imported_rig_bone_count":len(rig.data.bones),
        "imported_mesh_objects":len(meshes),
        "imported_skinned_mesh_count":len(skin),
        "tested_import_body_name":body.name,
        "tested_import_body_vertices":len(body.data.vertices),
        "independent_action_ranges":actions,
        "tested_action_frames":[first,middle,last],
        "actual_imported_body_max_motion_blender_world":round(motion,9),
        "actual_imported_body_restoration_residual_blender_world":round(restoration,9),
        "actual_imported_body_motion_pass":motion>0.001,
        "actual_imported_body_return_pass":restoration<=0.0005,
        "source_asset_material_count":len(body.data.materials),
        "source_native_file_reused":False,
        "actual_anatomical_completeness":"HOLD",
        "clinical_or_physical_units":"HOLD",
        "gait_and_tissue_physics":"HOLD",
        "cinematic_realism":"HOLD",
        "merge_release":"HOLD"
    }
    report["status"]="PASS_ACTUAL_COLD_IMPORTED_SKINNED_GLTF_MOTION_ONLY" if (
       report["actual_imported_body_motion_pass"] and report["actual_imported_body_return_pass"]) else (
       "FAIL_IMPORT_MOTION_OR_RETURN")
    scene.frame_set(first)
    scene.render.engine="CYCLES";scene.cycles.device="CPU";scene.cycles.samples=6
    scene.render.threads_mode="FIXED";scene.render.threads=4
    scene.render.resolution_x=384;scene.render.resolution_y=500
    # Rebuild a neutral proof camera; must not depend on source project file.
    from mathutils import Vector
    bbox=[body.matrix_world@Vector(corner) for corner in body.bound_box]
    center=sum(bbox,Vector())/len(bbox)
    zspan=max(v.z for v in bbox)-min(v.z for v in bbox)
    camera_data=bpy.data.cameras.new("R014_ColdGLB_Review")
    camera=bpy.data.objects.new("R014_ColdGLB_Review",camera_data)
    bpy.context.collection.objects.link(camera)
    camera_data.type="ORTHO";camera_data.ortho_scale=max(zspan*1.6,2.5)
    camera.location=(center.x,center.y-5.0,center.z)
    camera.rotation_euler=(center-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.camera=camera
    world=bpy.data.worlds.new("R014_ColdGLB_LitWorld")
    world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.7,0.73,0.78,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=0.8
    scene.world=world
    lamp=bpy.data.lights.new("R014_ColdGLB_Area","AREA")
    light=bpy.data.objects.new("R014_ColdGLB_Area",lamp)
    bpy.context.collection.objects.link(light)
    light.location=(center.x+1,center.y-3,center.z+2)
    lamp.energy=600;lamp.size=5
    scene.render.image_settings.file_format="PNG"
    for frame,title in [(first,"rest"),(middle,"posed")]:
        scene.frame_set(frame)
        frame_path=args.out/(args.sex+"_cold_glb_"+title+".png")
        scene.render.filepath=str(frame_path)
        bpy.ops.render.render(write_still=True)
        assert frame_path.stat().st_size>3000
        report.setdefault("new_scene_stills",[]).append({"name":frame_path.name,"sha256":sha(frame_path)})
    scene.frame_set(first)
    scene.render.filepath=""
    native=args.out/("R014_"+args.sex+"_cold_imported_GLTF_reeditable.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    report["independent_import_scene"]={"name":native.name,"sha256":sha(native),"bytes":native.stat().st_size}
    args.out.joinpath("cold_import_receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("R014_CC0_COLD_GLTF_IMPORT",json.dumps({
       "status":report["status"],"sex":args.sex,
       "imported_mesh":len(meshes),"skin":len(skin),
       "rig":len(rig.data.bones),"frames":[first,middle,last],
       "motion":report["actual_imported_body_max_motion_blender_world"],
       "rest_error":report["actual_imported_body_restoration_residual_blender_world"],
       "source_GLB_sha":report["source_exact_glb_sha256"]
    },sort_keys=True))
    if not report["status"].startswith("PASS_"):raise SystemExit("FAIL_CLOSED_GLTF_REPLAY")
if __name__=="__main__":main()
