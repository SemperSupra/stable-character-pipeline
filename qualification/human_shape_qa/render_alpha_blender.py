#!/usr/bin/env python3
"""Source-original R009 alpha silhouette stills: independent diagnostic evidence.

No protected identities, external images, scene references or downloaded costumes.
Full body and face masks use deterministic fixed cameras and REST joint pose.
Results are NOT evidence of realistic sex, biological anatomy, face identity or
motion accuracy; transparent pixels make cropping measurable.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ACTORS = ("AsterOriginal","JuniperOriginal")
ACTIVE = {"body","hair","style_top","style_bottom","footwear","accessory"}


def aim(camera, loc, at):
    camera.location=loc
    camera.rotation_euler=(Vector(at)-camera.location).to_track_quat("-Z","Y").to_euler()


def run(source,out,expected):
    source=Path(source).resolve()
    out=Path(out).resolve()
    raw=source.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=expected or raw[:4]!=b"glTF":
        raise ValueError("SHAPE_SOURCE_SHA_OR_FORMAT")
    out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    arms=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    if len(arms)!=2 or any(len(a.data.bones)!=35 for a in arms):
        raise RuntimeError("SHAPE_35_JOINT_IMPORT_REQUIRED")
    for arm in arms:arm.data.pose_position="REST"
    layers={}
    for o in bpy.data.objects:
        if o.type=="MESH" and "_Wardrobe_" in o.name:
            name,slot=o.name.split("_Wardrobe_",1)
            key=(name,slot.split(".")[0])
            if key in layers: raise RuntimeError("SHAPE_DUPLICATE_WARDROBE_SLOT")
            layers[key]=o
    scene=bpy.context.scene
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.render.resolution_x=768
    scene.render.resolution_y=768
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.render.film_transparent=True
    scene.frame_set(0)
    camera_data=bpy.data.cameras.new("R009AlphaEvidenceCamera")
    camera=bpy.data.objects.new("R009AlphaEvidenceCamera",camera_data)
    bpy.context.collection.objects.link(camera)
    camera_data.type="ORTHO"
    scene.camera=camera
    images=[]
    for actor,x,direction in (
            ("AsterOriginal",-3.35,1.),
            ("JuniperOriginal",3.35,-1.)):
        partner=[s for s in ACTORS if s!=actor][0]
        other=[o for o in bpy.data.objects if o.name.startswith(partner)]
        if len(other)<2:raise RuntimeError("SHAPE_PARTNER_ISOLATION")
        previous={o:o.hide_render for o in other}
        try:
            for o in other:o.hide_render=True
            present={slot for name,slot in layers if name==actor}
            if not {"body","hair","style_top","style_bottom","footwear"}.issubset(present):
                raise RuntimeError("SHAPE_REQUIRED_LAYERS")
            for (name,slot),obj in layers.items():
                if name==actor:obj.hide_render=slot not in ACTIVE
            for view in ("front","side","face"):
                if view=="front":
                    camera_data.ortho_scale=2.45
                    aim(camera,(x+direction*5,0,1.4),(x,0,.94))
                elif view=="side":
                    camera_data.ortho_scale=2.45
                    aim(camera,(x,5,1.4),(x,0,.94))
                else:
                    camera_data.ortho_scale=.74
                    aim(camera,(x+direction*2.5,0,1.67),(x,0,1.65))
                name=actor+"_"+view+"_alpha.png"
                path=out/name
                scene.render.filepath=str(path)
                bpy.ops.render.render(write_still=True)
                binary=path.read_bytes()
                if not binary.startswith(bytes([137,80,78,71,13,10,26,10])):
                    raise RuntimeError("SHAPE_NO_PNG")
                images.append({
                    "actor":actor,"view":view,"name":name,
                    "sha256":hashlib.sha256(binary).hexdigest(),
                    "bytes":len(binary),
                    "camera_ortho_scale":camera_data.ortho_scale,
                    "preset":"adventure",
                    "visual_anatomy_accepted":False
                })
        finally:
            for obj,old in previous.items():obj.hide_render=old
    if len(images)!=6:raise RuntimeError("SHAPE_MISSING_VIEWS")
    receipt={
        "schema":"scp.r009.source_original_alpha_masks.v1",
        "source_sha256":sha,"file_count":len(images),
        "images":images,"pose":"REST","pixels":"RGBA_FILM_TRANSPARENT",
        "blender_version":bpy.app.version_string,
        "full_body_anatomy_accepted":False,
        "face_identity_accepted":False,"garment_collision_accepted":False
    }
    (out/"alpha_index.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"file_count":len(images),"source_sha256":sha,
                      "schema":receipt["schema"],
                      "full_body_anatomy_accepted":False},sort_keys=True))


if __name__=="__main__":
    a=sys.argv[sys.argv.index("--")+1:]
    if len(a)!=3:raise SystemExit("USAGE GLB OUTDIR SHA")
    run(*a)
