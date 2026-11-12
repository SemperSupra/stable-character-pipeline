"""R014 actual MPFB six-morphology adult research: two independent 3-actor shards.

Creates *native* MPFB meshes and rigs with specified source macros, observable
animated skin deformation, native .blend, animated GLBs and CPU Cycles stills.
No claim about measured centimeters, complete anatomy, or photorealism.
"""
import argparse
import hashlib
import importlib
import json
import math
import struct
import sys
from pathlib import Path

import bpy
import addon_utils
from mathutils import Vector

SOURCE_SHA="6ff1eb358f6c1959ced77e79e6dd2406d9a71f49"
# These are independent synthetic adult body-design probes, never CPE concept
# labels or measured physical body dimensions; continuous MPFB macro values.
CASES={
  0:[
    {"name":"feminine_short_light","gender":0.0,"height":0.25,"weight":0.30,"muscle":0.35,"proportions":0.28},
    {"name":"feminine_tall_strong","gender":0.0,"height":0.78,"weight":0.62,"muscle":0.78,"proportions":0.65},
    {"name":"feminine_medium_full","gender":0.0,"height":0.52,"weight":0.82,"muscle":0.30,"proportions":0.23},
  ],
  1:[
    {"name":"masculine_short_broad","gender":1.0,"height":0.30,"weight":0.74,"muscle":0.65,"proportions":0.78},
    {"name":"masculine_tall_slim","gender":1.0,"height":0.82,"weight":0.27,"muscle":0.37,"proportions":0.70},
    {"name":"masculine_medium_strong","gender":1.0,"height":0.53,"weight":0.64,"muscle":0.84,"proportions":0.63},
  ],
}

def expose(suffix,name):
    for mod_name in list(sys.modules):
        if mod_name.endswith(suffix):
            m=importlib.import_module(mod_name)
            if hasattr(m,name):return getattr(m,name)
    raise RuntimeError("Unavailable pinned MPFB native API "+suffix+"::"+name)

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def bounds(obj):
    # local mesh-coordinate extents, not physical anthropometric measurements.
    coords=[v.co for v in obj.data.vertices]
    return [round(max(float(v[j]) for v in coords)-min(float(v[j]) for v in coords),6) for j in range(3)]

def meshpoints(obj):
    deps=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(deps)
    mesh=ev.to_mesh()
    try:
        mat=ev.matrix_world
        return [tuple(mat@v.co) for v in mesh.vertices]
    finally:ev.to_mesh_clear()

def pose_motion(rig,obj):
    bones=("upperarm01.L","upperleg01.L")
    scene=bpy.context.scene
    for bn in bones:
        assert bn in rig.pose.bones,("missing bone",bn)
        b=rig.pose.bones[bn];b.rotation_mode="XYZ"
        for frame,angle in ((1,0.0),(8,0.40 if bn=="upperarm01.L" else -0.25),(16,0.0)):
            b.rotation_euler=(0.0,angle,0.0)
            b.keyframe_insert(data_path="rotation_euler",frame=frame)
    scene.frame_set(1);bpy.context.view_layer.update()
    original=meshpoints(obj)
    scene.frame_set(8);bpy.context.view_layer.update()
    changed=meshpoints(obj)
    assert len(changed)==len(original)>1000
    diff=max(math.dist(a,b) for a,b in zip(original,changed))
    assert diff>0.0001,("no actuated skinned mesh",diff)
    scene.frame_set(16);bpy.context.view_layer.update()
    restored=meshpoints(obj)
    residual=max(math.dist(a,b) for a,b in zip(original,restored))
    assert residual<0.0001,("unreturned pose",residual)
    scene.frame_set(1)
    return {"posed_vertex_max_delta_blender_units":round(diff,7),
            "restored_vertex_max_residual_blender_units":round(residual,9),
            "frame_evidence":[1,8,16],"animated_bones":list(bones)}

def glbcontract(path):
    with path.open("rb") as f:
        magic,version,length=struct.unpack("<4sII",f.read(12))
        assert magic==b"glTF" and version==2 and length==path.stat().st_size
        chunk,kind=struct.unpack("<I4s",f.read(8))
        assert kind==b"JSON"
        gltf=json.loads(f.read(chunk))
    anim=gltf.get("animations",[])
    skins=gltf.get("skins",[])
    rot=sum(1 for a in anim for channel in a.get("channels",[])
            if channel.get("target",{}).get("path")=="rotation")
    assert anim and skins and rot,("GLB missing playable rig channels",path.name)
    return {"glb_sha256":sha(path),"glb_bytes":path.stat().st_size,
            "skins":len(skins),"animations":len(anim),"bone_rotation_channels":rot,
            "meshes":len(gltf.get("meshes",[]))}

def point_camera(cam,target):
    direction=Vector(target)-cam.location
    cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--shard",type=int,choices=(0,1),required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--receipt",type=Path,required=True)
    arg=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    arg.out.mkdir(parents=True,exist_ok=True)
    addon="bl_ext.r014lab.mpfb"
    if addon not in bpy.context.preferences.addons:
        addon_utils.enable(addon,default_set=False)
    assert addon in bpy.context.preferences.addons, "official MPFB unavailable"
    Human=expose("mpfb.services.humanservice","HumanService")
    Target=expose("mpfb.services.targetservice","TargetService")
    Props=expose("mpfb.entities.objectproperties","HumanObjectProperties")
    Export=expose("mpfb.services.exportservice","ExportService")
    Objects=expose("mpfb.services.objectservice","ObjectService")
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    report={
        "schema":"r014.mpfb.actual_six_body_kinematic_doe.v1",
        "mpfb_source_revision":SOURCE_SHA,
        "blender":bpy.app.version_string,
        "adult_character_design_asserted":True,
        "age_macro":0.65,
        "age_macro_is_not_chronological_age":True,
        "gender_macro_source_polity":"0.0 female-associated shape, 1.0 male-associated shape",
        "morph_source":"native normalized MPFB 0..1; not metric cm or actual user body",
        "shard":arg.shard,"characters":[],"status":"INCOMPLETE",
        "merge_release":"HOLD",
        "photoreal_acceptance":"HOLD_UNTEXTURED_RESEARCH",
        "anatomical_completeness":"UNQUALIFIED",
        "mesh_geometry_native":True,
        "source_is_pinned_and_licensed":True,
        "limits":["No real human measurements or identities","No medical age/sex inference",
                  "No clinical anatomical coverage or genital completeness",
                  "No photoreal skin, eyes, hair, teeth, garments or cinematography acceptance",
                  "No foot contact, knee anatomical limits, collision or soft tissue physics"]
    }
    scene=bpy.context.scene
    scene.frame_start=1;scene.frame_end=16;scene.render.fps=12
    bodies=[]
    for i,cfg in enumerate(CASES[arg.shard]):
        assert cfg["gender"]==(0.0 if arg.shard==0 else 1.0)
        for property in ("height","weight","muscle","proportions","gender"):
            assert 0.0<=cfg[property]<=1.0
        body=Human.create_human()
        for key in ("gender","height","weight","muscle","proportions"):
            Props.set_value(key,cfg[key],entity_reference=body)
        Props.set_value("age",0.65,entity_reference=body)
        Target.reapply_macro_details(body)
        rig=Human.add_builtin_rig(body,"default")
        body.name=cfg["name"]+"_source_body"
        rig.name=cfg["name"]+"_source_rig"
        rig.location.x=i*2.8
        bpy.context.view_layer.update()
        assert len(body.data.vertices)>1000 and len(rig.data.bones)>20
        assert len(body.vertex_groups)>20
        source_dims=bounds(body)
        root=Export.create_character_copy(body,name_suffix="_clean_export")
        clean=Objects.find_object_of_type_amongst_nearest_relatives(root,"Basemesh")
        assert clean and clean.type=="MESH"
        rawverts=len(clean.data.vertices)
        Export.bake_modifiers_remove_helpers(clean,bake_masks=True,bake_subdiv=False,
                                            remove_helpers=True,also_proxy=False)
        assert 1000<len(clean.data.vertices)<rawverts
        rigs=[m.object for m in clean.modifiers if m.type=="ARMATURE" and m.object]
        assert len(rigs)==1,("clean armature not unique",cfg["name"],len(rigs))
        cleanrig=rigs[0]
        assert len(cleanrig.data.bones)>20 and len(clean.vertex_groups)>20
        motion=pose_motion(cleanrig,clean)
        body.hide_render=True;rig.hide_render=True
        clean.name=cfg["name"]+"_clean_body"
        cleanrig.name=cfg["name"]+"_clean_rig"
        mesh_dims=bounds(clean)
        record={
            "case":cfg["name"],"source_macros":cfg,"age_macro":0.65,
            "source_vertices":len(body.data.vertices),
            "clean_vertices":len(clean.data.vertices),
            "source_bounds_xyz_blender_units":source_dims,
            "clean_bounds_xyz_blender_units":mesh_dims,
            "bone_count":len(cleanrig.data.bones),
            "deform_groups":len(clean.vertex_groups),
            "motion":motion
        }
        bodies.append((cfg,clean,cleanrig,record))
        report["characters"].append(record)
    scene.frame_set(1)
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=8
    scene.render.threads_mode="FIXED"
    scene.render.threads=4
    scene.render.resolution_x=320;scene.render.resolution_y=420
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    world=bpy.data.worlds.new("R014_SixMorphNeutralReview")
    world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.75,0.78,0.82,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=0.7
    scene.world=world
    lampdata=bpy.data.lights.new("R014_GenericAreaKey","AREA")
    lamp=bpy.data.objects.new("R014_GenericAreaKey",lampdata)
    bpy.context.collection.objects.link(lamp)
    lamp.location=(2.0,-3.5,4.0)
    lampdata.energy=750;lampdata.size=5
    camdata=bpy.data.cameras.new("R014_SixMorphReviewCamera")
    cam=bpy.data.objects.new("R014_SixMorphReviewCamera",camdata)
    bpy.context.collection.objects.link(cam)
    scene.camera=cam;camdata.type="ORTHO";camdata.ortho_scale=2.65
    native=arg.out/("R014_ThreeAdultMorphs_Shard"+str(arg.shard)+".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    report["native_blend"]={"filename":native.name,"sha256":sha(native),"bytes":native.stat().st_size}
    for i,(cfg,body,rig,record) in enumerate(bodies):
        bpy.ops.object.select_all(action="DESELECT")
        body.select_set(True);rig.select_set(True)
        bpy.context.view_layer.objects.active=rig
        glb=arg.out/(cfg["name"]+"_rig_animated.glb")
        bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",
            use_selection=True,export_animations=True,export_morph=True,
            export_skins=True,export_yup=True)
        record["portable_animated_glb"]=glbcontract(glb)
        for pose,view in ((1,"front"),(8,"side")):
            scene.frame_set(pose)
            bpy.context.view_layer.update()
            for _,other,_,_ in bodies:other.hide_render=(other!=body)
            x=i*2.8
            if view=="front":cam.location=(x,-5.8,1.7)
            else:cam.location=(x+5.8,-0.2,1.65)
            point_camera(cam,(x,0,1.03))
            image=arg.out/(cfg["name"]+"_"+view+"_pose"+str(pose)+".png")
            scene.render.filepath=str(image)
            bpy.ops.render.render(write_still=True)
            assert image.stat().st_size>2000
            record.setdefault("visual_files",[]).append({"name":image.name,"sha256":sha(image)})
    # Render short native actor-motion video on the final actor, not camera-only.
    _,hero,_,hero_record=bodies[-1]
    for _,other,_,_ in bodies:other.hide_render=(other!=hero)
    cam.location=((len(bodies)-1)*2.8,-5.8,1.7)
    point_camera(cam,((len(bodies)-1)*2.8,0,1.03))
    scene.frame_start=1;scene.frame_end=16
    scene.render.resolution_x=256;scene.render.resolution_y=340
    scene.render.image_settings.file_format="FFMPEG"
    scene.render.ffmpeg.format="MPEG4";scene.render.ffmpeg.codec="H264"
    scene.render.filepath=str(arg.out/("R014_morph_shard"+str(arg.shard)+"_actual_rig_motion.mp4"))
    bpy.ops.render.render(animation=True)
    movie=Path(scene.render.filepath)
    assert movie.is_file() and movie.stat().st_size>5000, "no actual H264 created"
    report["rig_motion_video"]={"filename":movie.name,"sha256":sha(movie),
        "bytes":movie.stat().st_size,"rendered_frames":16,
        "motion_kind":"actual skinned upper arm and leg joints; no locomotion"}
    report["status"]="PASS_NATIVE_MORPH_RIG_ANIMATION_EXPORT_AND_STILLS_ONLY"
    arg.receipt.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("R014_SIX_MORPH_BATCH",json.dumps(report,sort_keys=True))

if __name__=="__main__":main()
