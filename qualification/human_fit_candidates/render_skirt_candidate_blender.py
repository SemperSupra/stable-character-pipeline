#!/usr/bin/env python3
"""Fixed-camera native before/after ORIGINAL Juniper skirt candidate stills.

Source SHA exact, Blender 4.5, 35 joint rig, identical camera/lighting/pose
for unaltered baseline, only-Juniper 8%, and only-Juniper 14%. Original PNGs
are geometry observations, NOT a success claim for skirt fit or human likeness.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ACTOR="JuniperOriginal"
CANDIDATES=("baseline","juniper_skirt_8","juniper_skirt_14")
FRAMES=("front","side","waist")


def aim(camera,pos,at):
    camera.location=pos
    camera.rotation_euler=(Vector(at)-camera.location).to_track_quat("-Z","Y").to_euler()


def render(src,outdir,expected_sha,variant):
    if variant not in CANDIDATES:raise ValueError("UNKNOWN_SKIRT_VISUAL_CANDIDATE")
    src=Path(src).resolve();folder=Path(outdir).resolve()
    raw=src.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=expected_sha or raw[:4]!=b"glTF":
        raise RuntimeError("SKIRT_VISUAL_SHA_OR_FORMAT_MISMATCH")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(src))
    if len([o for o in bpy.data.objects if o.type=="ARMATURE"])!=2 or any(
            len(o.data.bones)!=35 for o in bpy.data.objects if o.type=="ARMATURE"):
        raise RuntimeError("SKIRT_VISUAL_EXPECTED_TWO_35_JOINT_RIGS")
    active={}
    for obj in bpy.data.objects:
        if obj.type!="MESH":continue
        if "_Wardrobe_" in obj.name:
            actor,slot=obj.name.split("_Wardrobe_",1)
            slot=slot.split(".")[0]
            if actor=="AsterOriginal":
                obj.hide_render=True
            elif actor==ACTOR:
                active[slot]=obj
            else:
                raise RuntimeError("SKIRT_VISUAL_FOREIGN_WARDROBE_OBJECT")
    required={"body","hair","footwear","style_top","style_bottom"}
    if set(active)!=required:
        raise RuntimeError("SKIRT_VISUAL_STRICT_MESH_PRESET_DRIFT:"+repr(active))
    for slot,obj in active.items():
        if len([m for m in obj.modifiers if m.type=="ARMATURE"])!=1:
            raise RuntimeError("SKIRT_VISUAL_UNSKINNED:"+slot)
    for obj in bpy.data.objects:
        if obj.name.startswith("AsterOriginal"):obj.hide_render=True
    scene=bpy.context.scene
    scene.frame_set(1)
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=768
    scene.render.resolution_y=768
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.render.film_transparent=False
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_cavity=True
    if scene.world is None:
        scene.world=bpy.data.worlds.new("OriginalJuniperSkirtEvidence")
    scene.world.color=(.22,.24,.28)
    camdata=bpy.data.cameras.new("OriginalJuniperSkirtFixedEvidence")
    cam=bpy.data.objects.new("OriginalJuniperSkirtFixedEvidence",camdata)
    bpy.context.collection.objects.link(cam)
    camdata.type="ORTHO"
    scene.camera=cam
    x=3.35
    result=[]
    folder.mkdir(parents=True,exist_ok=True)
    for view in FRAMES:
        if view=="front":
            camdata.ortho_scale=2.50
            aim(cam,(x-5,0,1.3),(x,0,.93))
        elif view=="side":
            camdata.ortho_scale=2.50
            aim(cam,(x,5,1.4),(x,0,.93))
        else:
            camdata.ortho_scale=.98
            aim(cam,(x-4,0,1.12),(x,0,.88))
        name="JuniperOriginal_"+variant+"_"+view+".png"
        path=folder/name
        scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        binary=path.read_bytes()
        if binary[:8]!=bytes((137,80,78,71,13,10,26,10)) or len(binary)<12000:
            raise RuntimeError("SKIRT_VISUAL_RENDER_NOT_PNG:"+name)
        result.append({"file":name,"sha256":hashlib.sha256(binary).hexdigest(),
                       "byte_count":len(binary),"view":view,
                       "camera_ortho_scale":camdata.ortho_scale,
                       "actor":ACTOR,"variant":variant,
                       "visual_quality_accepted":False})
    if len(result)!=3:raise RuntimeError("SKIRT_VISUAL_MISSING_CAMERA")
    record={"schema":"scp.r009.juniper_original_native_skirt_ablations.v1",
            "source_sha256":sha,"variant":variant,"actor":ACTOR,
            "frame":1,"blender_version":bpy.app.version_string,
            "images":result,"acceptance":"REQUIRES_INDEPENDENT_VISUAL_REVIEW",
            "body_cloth_clearance_accepted":False,
            "facial_anatomy_accepted":False,
            "source_original":True}
    (folder/("JuniperOriginal_"+variant+"_visual-index.json")).write_text(
        json.dumps(record,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"schema":record["schema"],"variant":variant,
                      "images":len(result),"source_sha256":sha,
                      "body_cloth_clearance_accepted":False},sort_keys=True))


if __name__=="__main__":
    args=sys.argv[sys.argv.index("--")+1:]
    if len(args)!=4:raise SystemExit("usage GLB OUTDIR SHA VARIANT")
    render(*args)
