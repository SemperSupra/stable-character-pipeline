#!/usr/bin/env python3
"""Native Blender independent portable-GLB scene/skin acceptance boundary.

Checks *active* layers and rig import, not appearance or cloth physics.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ACTORS=("AsterOriginal","JuniperOriginal")

def render_seam_evidence(folder,preset):
    """Technical camera witness, no human appearance approval.

    Camera axes use native Blender Z-up. Only signature/alt views are
    informative about garment seams; never render protected characters.
    """
    folder=Path(folder).resolve()
    folder.mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene
    if scene.world is None:
        scene.world=bpy.data.worlds.new("R009OriginalWardrobeTechnicalWorld")
    scene.world.color=(.22,.25,.29)
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.light="STUDIO"
    scene.display.shading.background_type="WORLD"
    scene.display.shading.show_shadows=True
    scene.render.resolution_x=720
    scene.render.resolution_y=480
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    end=int(round(max(float(a.frame_range[1]) for a in bpy.data.actions)))
    if end<70:
        raise ValueError("SOURCE_ANIMATION_TOO_SHORT_FOR_SEAM_QA")
    bpy.ops.object.camera_add(location=(0.,-6.,2.))
    camera=bpy.context.object
    camera.name="R009WardrobeSeamDiagnosticCamera"
    camera.data.type="ORTHO"
    camera.data.ortho_scale=2.55
    scene.camera=camera
    results=[]
    for actor in ACTORS:
        root=next((o for o in bpy.data.objects if o.name.startswith(actor+"_SceneRoot")),None)
        if root is None:
            raise ValueError("ACTOR_ROOT_MISSING_FOR_NATIVE_RENDER:"+actor)
        other=next(a for a in ACTORS if a!=actor)
        suppressed=[o for o in bpy.data.objects if o.name.startswith(other+"_")]
        old={o.name:o.hide_render for o in suppressed}
        for o in suppressed:o.hide_render=True
        try:
            for pose,frame in (("start",0),("end",end)):
                scene.frame_set(frame)
                bpy.context.view_layer.update()
                target=root.matrix_world.translation+Vector((0.,0.,1.02))
                forward=Vector((1.,0.,0.)) if actor==ACTORS[0] else Vector((-1.,0.,0.))
                for view,offset in (("front",forward*5.),
                                    ("oblique",forward*3.8+Vector((0.,-3.3,1.1)))):
                    camera.location=target+offset
                    camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
                    dest=folder/("wardrobe_"+preset+"_"+actor+"_"+pose+"_"+view+".png")
                    if dest.exists():raise FileExistsError("REFUSE_OVERWRITE_NATIVE_IMAGE")
                    scene.render.filepath=str(dest)
                    bpy.ops.render.render(write_still=True)
                    if not dest.exists() or dest.stat().st_size<2048:
                        raise ValueError("NATIVE_IMAGE_EMPTY")
                    results.append({"file":dest.name,
                         "sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
                         "bytes":dest.stat().st_size,
                         "actor":actor,"pose":pose,"frame":frame,
                         "view":view,"other_actor_hidden":True})
        finally:
            for o in suppressed:o.hide_render=old[o.name]
            bpy.context.view_layer.update()
    return results

def run(src,preset_receipt,out,render_dir=None):
    src=Path(src).resolve();out=Path(out).resolve()
    requested=json.loads(Path(preset_receipt).read_text())
    if requested.get("schema")!="scp.r009.original_wardrobe_preset_receipt.v1":
        raise ValueError("BAD_PORTABLE_RECEIPT")
    if requested.get("derived_sha256")!=hashlib.sha256(src.read_bytes()).hexdigest():
        raise ValueError("PORTABLE_SOURCE_SHA_MISMATCH")
    if src==out:raise ValueError("SOURCE_OVERWRITE_REFUSED")
    if out.exists():raise FileExistsError("REFUSE_OVERWRITE_NATIVE_RECEIPT")
    bpy.ops.import_scene.gltf(filepath=str(src))
    observed={a:set() for a in ACTORS}
    for ob in bpy.data.objects:
        if ob.type!="MESH":continue
        name=ob.name if "_Wardrobe_" in ob.name else ob.data.name
        if "_Wardrobe_" not in name:continue
        actor,slot=name.split("_Wardrobe_",1)
        slot=slot.split(".")[0]
        if actor not in observed:raise ValueError("UNKNOWN_ACTOR")
        observed[actor].add(slot)
        mods=[m for m in ob.modifiers if m.type=="ARMATURE"]
        if len(mods)!=1 or len(mods[0].object.data.bones)!=35:
            raise ValueError("PORTABLE_SKIN_IMPORT_FAIL")
    for actor in ACTORS:
        wanted=set(requested["active_layers"][actor])
        if observed[actor]!=wanted:
            raise ValueError("PORTABLE_SCENE_LAYER_MISMATCH:"+actor+
                             ":"+str(sorted(observed[actor]))+"!="+str(sorted(wanted)))
        if not {"body","hair"}.issubset(observed[actor]):
            raise ValueError("PORTABLE_BODY_MISSING")
    result={"schema":"scp.r009.original_portable_native.v2",
        "source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
        "actors":{a:sorted(observed[a]) for a in ACTORS},
        "joint_count_per_actor":35,"scene_skin_import":"PASS",
        "visual_garment_body_intersection":"UNKNOWN_NOT_MEASURED",
        "human_appearance_accepted":False}
    if render_dir:
        result["diagnostic_images"]=render_seam_evidence(render_dir,
            requested["presets"][ACTORS[0]])
        result["native_technical_images_produced"]=len(result["diagnostic_images"])
        result["human_appearance_accepted"]=False
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--portable-receipt",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--render-dir",help="Optional 2-actor native seam PNG diagnostic folder")
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    print(json.dumps(run(args.input,args.portable_receipt,args.out,args.render_dir),sort_keys=True))
