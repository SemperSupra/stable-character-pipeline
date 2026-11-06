#!/usr/bin/env python3
"""Exact-source Blender face before/after four PNG source-pinned pixel witness.

Native preview only: no face identity, photorealism, sex classification,
biometric verification or medical outcome inference. Never regenerates a
private person or repurposes a protected source.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ACTORS=("AsterOriginal","JuniperOriginal")
SCHEMA="scp.r009.original_face_delta_native.v1"


def aim(camera,loc,target):
    camera.location=loc
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()


def count_changes(before,after,threshold=.042):
    if len(before)!=len(after) or len(before)%4:
        raise RuntimeError("FACE_PIXEL_SHAPE_MISMATCH")
    count=0
    for j in range(0,len(before),4):
        if max(abs(before[j+k]-after[j+k]) for k in range(3))>threshold:
            count+=1
    return count


def selftest():
    a=[0.,.2,.1,1.,.5,.5,.5,1.]
    b=[0.,.2,.1,1.,.7,.5,.5,1.]
    if count_changes(a,a)!=0 or count_changes(a,b)!=1:
        raise RuntimeError("FACE_PIXEL_ORACLE_BAD")
    if count_changes(a,b,threshold=1)!=0:
        raise RuntimeError("FACE_PIXEL_THRESHOLD_BAD")
    print(json.dumps({"schema":SCHEMA+".negative_test",
                      "identical_pixels":0,"one_changed_pixel":1,
                      "science_accepted":False}))


def render(source,actor,heading,out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    arms=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    if len(arms)!=2 or any(len(a.data.bones)!=35 for a in arms):
        raise RuntimeError("FACE_NATIVE_ACTOR_RIG_INVALID")
    for arm in arms:arm.data.pose_position="REST"
    # Only body/hair; face and hair must be attributed to the same 35-joint
    # original actor. The rest of this experiment is wardrobe-agnostic.
    meshes=[o for o in bpy.data.objects if o.type=="MESH" and "_Wardrobe_" in o.name]
    active=[]
    for o in meshes:
        if o.name.startswith(actor+"_Wardrobe_"):
            slot=o.name.split("_Wardrobe_",1)[1].split(".")[0]
            if slot in ("body","hair"):
                active.append(o)
            else:
                o.hide_render=True
        else:
            o.hide_render=True
    if len(active)!=2 or set(o.name.split("_Wardrobe_",1)[1].split(".")[0]
                            for o in active)!={"body","hair"}:
        raise RuntimeError("FACE_NATIVE_BODY_HAIR_REQUIRED")
    if not all(any(m.type=="ARMATURE" for m in o.modifiers) for o in active):
        raise RuntimeError("FACE_NATIVE_MESH_NOT_SKINNED")
    scene=bpy.context.scene
    scene.frame_set(0)
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_cavity=True
    scene.render.resolution_x=640
    scene.render.resolution_y=640
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.render.film_transparent=False
    camera_data=bpy.data.cameras.new("R009FaceFixedSourceCamera")
    camera=bpy.data.objects.new("R009FaceFixedSourceCamera",camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera=camera
    camera_data.type="ORTHO"
    camera_data.ortho_scale=.65
    actor_x=-3.35 if actor=="AsterOriginal" else 3.35
    aim(camera,(actor_x+heading*2.,0.,1.72),(actor_x,0.,1.65))
    scene.render.filepath=str(out)
    bpy.ops.render.render(write_still=True)
    raw=Path(out).read_bytes()
    if len(raw)<10000 or not raw.startswith(bytes([137,80,78,71,13,10,26,10])):
        raise RuntimeError("FACE_NATIVE_NOT_PNG")
    picture=bpy.data.images.load(str(out),check_existing=False)
    try: pixels=tuple(picture.pixels[:])
    finally: bpy.data.images.remove(picture)
    return {"name":out.name,
            "sha256":hashlib.sha256(raw).hexdigest(),
            "size":len(raw),
            "source_glb_sha256":hashlib.sha256(Path(source).read_bytes()).hexdigest(),
            "actor":actor,
            "native_rig_joints_each":35},pixels


def qualify(before,after,outdir,before_sha,after_sha):
    a,b=Path(before).resolve(),Path(after).resolve()
    if a==b or before_sha==after_sha:
        raise ValueError("FACE_NO_COUNTERFACTUAL")
    outdir=Path(outdir).resolve()
    for source,expected in ((a,before_sha),(b,after_sha)):
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
            raise ValueError("FACE_NATIVE_SOURCE_SHA")
    outdir.mkdir(parents=True,exist_ok=True)
    images={}
    differences={}
    for actor,heading in (("AsterOriginal",1.),("JuniperOriginal",-1.)):
        first,outpixels=render(a,actor,heading,outdir/(actor+"_baseline_face.png"))
        second,inpixels=render(b,actor,heading,outdir/(actor+"_candidate_face.png"))
        if first["sha256"]==second["sha256"]:
            raise RuntimeError("FACE_NATIVE_IDENTICAL_RENDER:"+actor)
        changed=count_changes(outpixels,inpixels)
        if changed<100:
            raise RuntimeError("FACE_NATIVE_INSUFFICIENT_VISIBLE_PIXEL_EFFECT:"+actor)
        images[actor]={"baseline":first,"candidate":second}
        differences[actor]={
            "changed_pixels_RGB_gt_0.042":changed,
            "resolution_pixels":640*640,
            "differential_geometry_visibility":"PASS_MEASURABLE_PIXEL_DELTA",
            "artist_quality_accepted":False
        }
    receipt={
        "schema":SCHEMA,"before_sha256":before_sha,
        "after_sha256":after_sha,
        "actor_images":images,
        "differential_pixel_tests":differences,
        "blender_version":bpy.app.version_string,
        "same_camera_same_original_actor_rest_pose":True,
        "sex_inferred_from_image":False,
        "artistic_face_quality_accepted":False,
        "medical_procedure_simulation_accepted":False,
        "fully_rigged_facial_motion_accepted":False,
        "body_garment_fit_accepted":False,
        "owner_rights_release_merge_cpe_held":True,
    }
    (outdir/"face_delta_native_receipt.json").write_text(
        json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"schema":SCHEMA,"before_sha256":before_sha,
                      "after_sha256":after_sha,
                      "changed_pixels":{actor:d["changed_pixels_RGB_gt_0.042"]
                                        for actor,d in differences.items()},
                      "face_visual_accepted":False},sort_keys=True))


if __name__=="__main__":
    args=sys.argv[sys.argv.index("--")+1:]
    if args==["--selftest"]:
        selftest()
    elif len(args)==5:
        qualify(*args)
    else:
        raise SystemExit("usage: -- BASE_GLB CANDIDATE_GLB OUTDIR SHA_BASE SHA_CANDIDATE or --selftest")
