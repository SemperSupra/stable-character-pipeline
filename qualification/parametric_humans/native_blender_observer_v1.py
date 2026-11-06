#!/usr/bin/env python3
"""Independent Blender GLB import and 2-view/2-pose technical witness.

Runs as: blender -b --factory-startup --python-exit-code 9 --python SCRIPT
         -- --input GLB --out-dir DIRECTORY --label before|after
Never claims visual, anatomical, garment, surgery, or CPE acceptance.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SCHEMA="scp.r009.parametric_native_blender_observer.v1"

def check(condition, reason):
    if not condition:
        raise RuntimeError(reason)

def observe(path, out_dir, label):
    check(label in ("before", "after"),"INVALID_LABEL")
    check(path.is_file() and path.stat().st_size > 1024,"INPUT_MISSING_OR_TOO_SMALL")
    out_dir.mkdir(parents=True,exist_ok=True)
    target=out_dir/(label+"_native_blender.json")
    check(not target.exists(),"REFUSE_OVERWRITE_RECEIPT")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    arms=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    meshes=[o for o in bpy.data.objects if o.type=="MESH"]
    check(len(arms)>=2,"TWO_ARMATURES_NOT_IMPORTED")
    check(len(meshes)>=8,"MESH_LAYER_COVERAGE_NOT_IMPORTED")
    named={m.name for m in bpy.data.materials}
    eye_names=[
        actor+"_"+side+"_iris_parametric"
        for actor in ("AsterOriginal","JuniperOriginal")
        for side in ("left","right")
    ]
    missing=[n for n in eye_names if not any(m.startswith(n) for m in named)]
    check(not missing,"SEPARATE_IRIS_MATERIALS_MISSING:"+repr(missing))
    for actor in ("AsterOriginal","JuniperOriginal"):
        for mat in ("skinWarm" if actor=="AsterOriginal" else "skinCool",
                    "ebonyHair" if actor=="AsterOriginal" else "chestnutHair"):
            check(any(m.startswith(actor+"_"+mat+"_parametric") for m in named),
                  "SKIN_HAIR_MATERIAL_MISSING:"+actor+":"+mat)
    roots={actor:next((o for o in bpy.data.objects
                  if o.name.startswith(actor+"_SceneRoot")),None)
           for actor in ("AsterOriginal","JuniperOriginal")}
    check(all(roots.values()),"SOURCE_ROOT_IMPORT_MISSING")
    scene=bpy.context.scene
    animation_ends=[float(action.frame_range[1]) for action in bpy.data.actions]
    check(animation_ends and max(animation_ends)>1,"GLTF_ANIMATION_NOT_IMPORTED")
    end=int(round(max(animation_ends)))
    start=0
    def separation(frame):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        a,b=(roots[key].matrix_world.translation for key in ("AsterOriginal","JuniperOriginal"))
        return (a-b).length
    initial=separation(start);final=separation(end)
    check(math.isfinite(initial) and math.isfinite(final) and initial-final>2.,
          "NATIVE_ACTORS_NOT_APPROACHING")
    # Workbench output is an observable original geometry/material swatch,
    # not photorealistic PBR/skin calibration.
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.light="STUDIO"
    scene.display.shading.show_shadows=True
    scene.display.shading.background_type="VIEWPORT"
    scene.display.shading.background_color=(.19,.22,.26)
    scene.display.shading.show_cavity=True
    scene.render.resolution_x=720
    scene.render.resolution_y=480
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    bpy.ops.object.camera_add(location=(0.,-11.,2.6))
    camera=bpy.context.object
    camera.name="R009TechnicalEvidenceCamera"
    camera.data.type="ORTHO"
    camera.data.ortho_scale=8.3
    scene.camera=camera
    saved=[]
    for pose,frame in (("start",start),("end",end)):
        scene.frame_set(frame)
        for view,loc in (("front",(0.,-11.5,2.5)),("oblique",(7.0,-9.0,3.0))):
            camera.location=loc
            point=Vector((0.,0.,1.05))
            direction=point-camera.location
            camera.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
            dest=out_dir/(label+"_"+pose+"_"+view+".png")
            check(not dest.exists(),"REFUSE_OVERWRITE_RENDER")
            scene.render.filepath=str(dest)
            bpy.ops.render.render(write_still=True)
            check(dest.is_file() and dest.stat().st_size>2000,"NATIVE_RENDER_MISSING_OR_EMPTY")
            saved.append({"file":dest.name,"sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
                         "bytes":dest.stat().st_size,"frame":frame,"view":view})
    # Independent closeups reveal face/garment geometry that the 2-actor
    # overview cannot resolve, especially when actors are far apart.
    scene.frame_set(end)
    bpy.context.view_layer.update()
    camera.data.ortho_scale=2.65
    for actor in ("AsterOriginal","JuniperOriginal"):
        actor_xyz=roots[actor].matrix_world.translation.copy()
        target=actor_xyz+Vector((0.,0.,.95))
        for view,offset in (("detail_front",Vector((0.,-5.0,1.0))),
                            ("detail_oblique",Vector((3.1,-4.2,1.5)))):
            camera.location=target+offset
            camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
            dest=out_dir/(label+"_"+actor+"_"+view+".png")
            check(not dest.exists(),"REFUSE_OVERWRITE_RENDER")
            scene.render.filepath=str(dest)
            bpy.ops.render.render(write_still=True)
            check(dest.is_file() and dest.stat().st_size>2000,"NATIVE_DETAIL_RENDER_MISSING")
            saved.append({"file":dest.name,
                         "sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
                         "bytes":dest.stat().st_size,
                         "frame":end,"view":view,"actor":actor})
    scene.camera.data.ortho_scale=8.3
    receipt={
        "schema":SCHEMA,"label":label,"source_sha256":source_sha,
        "blender_version":bpy.app.version_string,"render_engine":scene.render.engine,
        "imported_armatures":len(arms),"imported_meshes":len(meshes),
        "imported_actions":len(animation_ends),
        "per_actor_per_eye_materials_confirmed":True,
        "initial_source_root_separation":initial,
        "final_source_root_separation":final,
        "animation_end_frame":end,
        "generated_renders":saved,
        "native_import_render_technical_pass":True,
        "native_diagnostic_camera": "BLENDER_Z_UP_FRONT_NEGATIVE_Y",
        "closeups_generated":True,
        "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
        "geometry_material_source_unchanged":True,
        "anatomical_quality_accepted":False,
        "human_visual_accepted":False,
        "cloth_body_collision_qualified":False,
        "rig_retarged_for_morphology":False,
        "medical_surgery_prediction":False,
        "release_approved":False
    }
    with target.open("x",encoding="utf-8") as w:
        w.write(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("R009_BLENDER_TECHNICAL_WITNESS "+json.dumps({
        "label":label,"source_sha256":source_sha,
        "armatures":len(arms),"meshes":len(meshes),
        "initial_separation":round(initial,4),"final_separation":round(final,4),
        "end_frame":end,"render_count":len(saved),"human_visual_accepted":False},sort_keys=True))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True,type=Path)
    ap.add_argument("--out-dir",required=True,type=Path)
    ap.add_argument("--label",required=True,choices=("before","after"))
    args=ap.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    observe(args.input,args.out_dir,args.label)
