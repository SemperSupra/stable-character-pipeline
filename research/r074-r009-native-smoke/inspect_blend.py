#!/usr/bin/env python3
"""Source-original R009 two-actor native Blender save/reopen and gait witness.

Dedicated to MVP-blocker diagnostics. No protected source, license promotion,
human identity, actual Naomi/Alison, issuer signature or film acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def filehash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fail(condition, code):
    if condition:
        raise RuntimeError(code)


def paired_native():
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    groups = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        for modifier in o.modifiers:
            if modifier.type == "ARMATURE" and modifier.object in arms:
                groups.setdefault(modifier.object.name, []).append(o)
    fail(len(arms) != 2, "NATIVE_ACTOR_COUNT_NOT_TWO")
    fail(len(groups) != 2, "SKIN_MESH_NOT_BOUND_TO_TWO_ACTORS")
    fail(any(len(arm.data.bones) < 17 for arm in arms), "NATIVE_RIG_TOO_FEW_BONES")
    return sorted(arms, key=lambda a:a.name), groups


def scene_points(mesh, depsgraph):
    obj = mesh.evaluated_get(depsgraph)
    evaluated = obj.to_mesh()
    try:
        size = len(evaluated.vertices)
        fail(size == 0, "NATIVE_EMPTY_SKIN")
        mat = obj.matrix_world
        # Whole mesh not random index sample: no non-rigid false-pass.
        points = [mat @ v.co for v in evaluated.vertices]
        fail(any(not all(math.isfinite(d) for d in p) for p in points), "NONFINITE_NATIVE_SKIN")
        min_z = min(v.z for v in points)
        x_min = min(v.x for v in points)
        x_max = max(v.x for v in points)
        # deterministic vertex-pair spacing, independent of actor root travel
        stride = max(1,size//7)
        key = (points[0]-points[min(stride,size-1)]).length
        return {"vertices": size, "min_z_m":round(min_z,7),
                "center_x_m":round((x_min+x_max)/2,7),
                "pair_distance_m":round(key,7)}
    finally:
        obj.to_mesh_clear()


def inspect(saved, saved_sha, original_sha, output):
    fail(filehash(saved) != saved_sha, "SAVED_SCENE_SHA_MISMATCH")
    bpy.ops.wm.open_mainfile(filepath=str(Path(saved).resolve()),load_ui=False,use_scripts=False)
    fail(filehash(saved) != saved_sha, "SAVED_SCENE_BYTES_CHANGED_ON_OPEN")
    fail(bpy.context.scene.frame_end != 71 or bpy.context.scene.frame_start != 0,
         "NATIVE_FRAME_RANGE_MISMATCH")
    fail(bpy.context.scene.render.fps != 12, "NATIVE_FPS_MISMATCH")
    arms, groups = paired_native()
    scene=bpy.context.scene
    # Witness belongs to this ORIGINAL synthetic scene; a source-authoritative
    # floor height is not inferred from an actor bounding box or pixel mask.
    floor=bpy.data.objects.get("R074_OriginalPathGround")
    fail(floor is None or floor.type!="MESH", "NATIVE_SOURCE_FLOOR_MISSING")
    floor_z=max((floor.matrix_world @ Vector(corner)).z for corner in floor.bound_box)
    fail(not math.isfinite(floor_z) or abs(floor_z)>1e-5, "NATIVE_FLOOR_REFERENCE_CHANGED")
    observed=[]
    for frame in (0.,.125,12.,24.,24.125,36.,48.,48.125,71.):
        scene.frame_set(int(frame),subframe=frame-int(frame))
        depsgraph=bpy.context.evaluated_depsgraph_get()
        entry={"frame":frame,"actors":[]}
        for arm in arms:
            meshes=groups[arm.name]
            parts=[scene_points(m,depsgraph) for m in meshes]
            total=sum(p["vertices"] for p in parts)
            x=sum(p["center_x_m"]*p["vertices"] for p in parts)/total
            lowest=min(p["min_z_m"] for p in parts)
            entry["actors"].append({"armature":arm.name,"vertices":total,
                "min_z_m":round(lowest,7),"mean_mesh_center_x_m":round(x,7),
                "pair_distances_m":[p["pair_distance_m"] for p in parts]})
        observed.append(entry)
    start=observed[0]["actors"];end=observed[-1]["actors"]
    separation_start=abs(start[0]["mean_mesh_center_x_m"]-start[1]["mean_mesh_center_x_m"])
    separation_end=abs(end[0]["mean_mesh_center_x_m"]-end[1]["mean_mesh_center_x_m"])
    fail(separation_start < 1. or separation_end >= separation_start-0.5,
         "TWO_ACTOR_NATIVE_APPROACH_NOT_PROVEN")
    ground_min=min(actor["min_z_m"] for p in observed for actor in p["actors"])
    floor_relative=ground_min-floor_z
    floor_class=("FLOATING_GLOBAL_PROXY_GT_5MM" if floor_relative>0.005
        else "PENETRATING_GLOBAL_PROXY_GT_1MM" if floor_relative<-.001
        else "NEAR_FLOOR_PROXY_UNQUALIFIED")
    motion=max(abs(start[i]["pair_distances_m"][j]-end[i]["pair_distances_m"][j])
               for i in range(2) for j in range(len(start[i]["pair_distances_m"])))
    result={
        "schema":"scp.r074.r009-native-mvp-contact-scout.v1",
        "status":"HOLD_NATIVE_CONTACT_AND_GAIT",
        "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
        "protected_real_characters":False,"mvp_accepted":False,
        "source_glb_sha256":original_sha,"saved_blend_sha256":saved_sha,
        "loaded_with_scripts_disabled":True,"actor_count":len(arms),
        "animated_approach":{"separation_start_m":separation_start,
                             "separation_end_m":separation_end},
        "source_native_skin_pair_max_delta_m":motion,
        "ground_clearance_min_m":ground_min,
        "source_floor_top_z_m":floor_z,
        "minimum_mesh_to_floor_proxy_m":floor_relative,
        "floor_proxy_classification":floor_class,
        "sampled_fractional_frames":True,
        "ground_contact_qualified":False,"heel_toe_qualified":False,
        "source_kinematic_envelope_qualified":False,
        "new_source_motion_accepted":False,
        "dle":"SemperSupra/stable-character-pipeline-private#23",
        "scope":"R009_ORIGINAL_SYNTHETIC_SCOUT_NOT_PROTECTED_PRODUCTION",
        "observations":observed,
    }
    Path(output).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print("R074_NATIVE_SCOUT",json.dumps({k:result[k] for k in
        ("status","actor_count","animated_approach","source_native_skin_pair_max_delta_m","ground_clearance_min_m")},sort_keys=True))


def build(glb,expected,saved,out):
    fail(filehash(glb) != expected, "INPUT_GLB_SHA_MISMATCH")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(glb).resolve()))
    paired_native()
    scene=bpy.context.scene
    scene.frame_start=0;scene.frame_end=71;scene.render.fps=12
    # Source-original explicit level park path: top face exactly Z=0m.
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-0.02))
    floor=bpy.context.object
    floor.name="R074_OriginalPathGround"
    floor.dimensions=(12,2.4,.04)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=480
    scene.render.resolution_y=270
    scene.render.resolution_percentage=100
    camera_data=bpy.data.cameras.new("OriginalR009EvidenceCamera")
    cam=bpy.data.objects.new("OriginalR009EvidenceCamera",camera_data)
    bpy.context.collection.objects.link(cam)
    cam.location=(0.,12.,3.)
    direction=Vector((0,0,1.0))-cam.location
    cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
    camera_data.type="ORTHO";camera_data.ortho_scale=9.5
    scene.camera=cam
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(saved).resolve()))
    # Three actual native preview frames; 72-frame full motion is verified by
    # the sampled evaluated 3D scene, not misrepresented by this video smoke.
    frames=Path(out).parent/"frames"
    frames.mkdir(parents=True,exist_ok=True)
    for idx,frame in enumerate((0,36,71)):
        scene.frame_set(frame)
        scene.render.filepath=str(frames/f"frame_{idx:03d}.png")
        bpy.ops.render.render(write_still=True)
    rec={"schema":"scp.r074.native-source-build.v1","glb_sha256":expected,
         "saved_blend_sha256":filehash(saved),
         "scene_frames":72,"camera_source":"ORIGINAL_SYNTHETIC",
         "mvp_accepted":False}
    Path(out).write_text(json.dumps(rec,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("R074_BUILT",json.dumps(rec,sort_keys=True))


def main():
    args=sys.argv[sys.argv.index("--")+1:]
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("build","inspect"),required=True)
    p.add_argument("--glb");p.add_argument("--glb-sha")
    p.add_argument("--saved",required=True);p.add_argument("--saved-sha")
    p.add_argument("--out",required=True)
    a=p.parse_args(args)
    if a.mode=="build":
        fail(not a.glb or not a.glb_sha, "SOURCE_GLB_REQUIRED")
        build(a.glb,a.glb_sha,a.saved,a.out)
    else:
        fail(not a.saved_sha or not a.glb_sha, "SAVED_INPUT_PINS_REQUIRED")
        inspect(a.saved,a.saved_sha,a.glb_sha,a.out)

if __name__=="__main__":
    main()
