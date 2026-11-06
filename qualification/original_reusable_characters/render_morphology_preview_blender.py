#!/usr/bin/env python3
"""Tiny native Blender qualification of ORIGINAL R009 character silhouettes.

Generates 10 fixed-camera, isolated actor comparison stills: original signature
and custom adventure garment, face/full-body/oblique/side. NOT human acceptance.
No source rights promotion, photorealistic claims, or private files.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ACTORS = ("AsterOriginal", "JuniperOriginal")
PRESETS = {
    "signature": {"body","hair","top","bottom","footwear","accessory"},
    "adventure": {"body","hair","style_top","style_bottom","footwear","accessory"},
}
EXPECTED_SLOTS = {"body", "hair", "top", "bottom", "footwear",
                  "alt_top", "alt_bottom", "style_top", "style_bottom"}


def aim(camera, location, target):
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat(
        "-Z", "Y").to_euler()


def run(src, output_dir, source_sha):
    src = Path(src).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    if hashlib.sha256(data).hexdigest() != source_sha:
        raise RuntimeError("PREVIEW_INPUT_DIGEST_MISMATCH")
    if data[:4] != b"glTF":
        raise RuntimeError("PREVIEW_NOT_GLTF")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(src))
    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(armatures) != 2 or any(len(a.data.bones) != 35 for a in armatures):
        raise RuntimeError("PREVIEW_EXPECTED_TWO_35_BONE_RIGS")
    for a in armatures:
        a.data.pose_position = "REST"

    layers = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH" or "_Wardrobe_" not in obj.name:
            continue
        actor, slot = obj.name.split("_Wardrobe_", 1)
        slot = slot.split(".")[0]
        if actor not in ACTORS:
            raise RuntimeError("PREVIEW_FOREIGN_ACTOR")
        if (actor, slot) in layers:
            raise RuntimeError("PREVIEW_DUPLICATE_SLOT")
        layers[(actor, slot)] = obj
    for actor in ACTORS:
        slots = {slot for a, slot in layers if a == actor}
        if not EXPECTED_SLOTS <= slots:
            raise RuntimeError("PREVIEW_MISSING_NEW_GARMENT:" + actor)
        for slot in ("body", "top", "style_top", "style_bottom"):
            if not any(m.type == "ARMATURE" for m in layers[(actor,slot)].modifiers):
                raise RuntimeError("PREVIEW_UNSKINNED_LAYER:"+actor+":"+slot)

    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = 71
    scene.frame_set(0)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    if scene.world is None:
        scene.world = bpy.data.worlds.new("SourceOriginalCharacterReview")
    scene.world.color = (.22,.24,.28)
    camera_data = bpy.data.cameras.new("R009FixedReviewCamera")
    camera = bpy.data.objects.new("R009FixedReviewCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"

    results = []
    for actor, x, heading in (("AsterOriginal", -3.35, 1.),
                              ("JuniperOriginal", 3.35, -1.)):
        other = [o for o in ACTORS if o != actor][0]
        other_objects = [o for o in bpy.data.objects if o.name.startswith(other)]
        if len(other_objects) < 2:
            raise RuntimeError("PREVIEW_PARTNER_ISOLATION_FAILED")
        saved = {o:o.hide_render for o in other_objects}
        try:
            for o in other_objects:
                o.hide_render = True
            for preset, view in (
                ("signature","front"), ("adventure","front"),
                ("adventure","oblique"), ("adventure","side"),
                ("adventure","face"),
            ):
                for (a,slot),obj in layers.items():
                    if a == actor:
                        obj.hide_render = slot not in PRESETS[preset]
                if view == "front":
                    camera_data.ortho_scale=2.5
                    aim(camera,(x+heading*5.,0.,1.3),(x,0.,.93))
                elif view == "oblique":
                    camera_data.ortho_scale=2.5
                    aim(camera,(x+heading*4.,3.,1.5),(x,0.,.93))
                elif view == "side":
                    camera_data.ortho_scale=2.5
                    aim(camera,(x,5.,1.4),(x,0.,.93))
                else:
                    camera_data.ortho_scale=.74
                    aim(camera,(x+heading*2.,0.,1.70),(x,0.,1.66))
                filename=f"{actor}_{preset}_{view}.png"
                file=output_dir/filename
                scene.render.filepath=str(file)
                bpy.ops.render.render(write_still=True)
                raw=file.read_bytes()
                if not raw.startswith(b"\\x89PNG\\r\\n\\x1a\\n") or len(raw)<10000:
                    raise RuntimeError("PREVIEW_NOT_REAL_PNG:"+filename)
                active=sorted(s for (a,s),o in layers.items()
                              if a == actor and not o.hide_render)
                if not {"body","hair","footwear"}.issubset(active):
                    raise RuntimeError("PREVIEW_BASE_GONE")
                results.append({
                    "name":filename, "sha256":hashlib.sha256(raw).hexdigest(),
                    "bytes":len(raw), "actor":actor, "preset":preset,
                    "view":view, "active_layers":active,
                    "visual_accepted":False
                })
        finally:
            for o,previous in saved.items():
                o.hide_render=previous
    if len(results) != 10:
        raise RuntimeError("PREVIEW_MISSING_VIEWS")
    scene.camera=camera
    # Native editable deliverable, not a flattened image masquerading as a model.
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir/"morphology_costumes_editable.blend"))
    report={
        "schema":"scp.r009.morphology_blender_preview.v1",
        "input_sha256":source_sha,
        "source_kind":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
        "blender_version":bpy.app.version_string,
        "armature_counts":{a.name:len(a.data.bones) for a in armatures},
        "file_count":len(results), "images":results,
        "visual_anatomy_accepted":False,
        "garment_clipping_accepted":False,
        "physical_cloth_accepted":False,
        "scientific_status":"RENDERED_FOR_INDEPENDENT_REVIEW"
    }
    (output_dir/"native_preview_receipt.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "schema":report["schema"],"file_count":len(results),
        "input_sha256":source_sha,
        "blender_version":bpy.app.version_string,
        "visual_anatomy_accepted":False
    },sort_keys=True))

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--")+1:]
    if len(argv)!=3:
        raise SystemExit("USAGE: GLB OUTPUT_DIR EXPECTED_SHA256")
    run(*argv)
