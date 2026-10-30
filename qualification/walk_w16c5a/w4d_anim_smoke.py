"""W4D: Blender-native ORIGINAL synthetic two-actor 24-frame skin animation.

Only a liveness/interop test. Deliberately NOT C5B grounded source motion,
anatomical locomotion, an approved real person, or an L1 accepted human clip.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import bpy
from mathutils import Quaternion
from native_sole import add_actor, ACTORS, LEGS

def evaluated_positions(obj):
    bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get()
    e=obj.evaluated_get(deps);mesh=e.to_mesh()
    try:
        return [tuple(float(v) for v in e.matrix_world@p.co) for p in mesh.vertices]
    finally:
        e.to_mesh_clear()

def generate(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.frame_start=0;scene.frame_end=23;scene.render.fps=12
    assets=[add_actor(name,x) for name,x in ACTORS]
    observations={}
    for tick in range(24):
        scene.frame_set(tick)
        for ai,(arm,mesh,marks) in enumerate(assets):
            for li,(leg,sign) in enumerate(LEGS):
                bone=arm.pose.bones[leg+"Lower"]
                angle=.17*math.sin(2*math.pi*tick/24+li*math.pi+ai*.25)
                bone.rotation_mode="QUATERNION"
                bone.rotation_quaternion=Quaternion((1,0,0),angle)
                bone.keyframe_insert(data_path="rotation_quaternion",frame=tick)
            arm.keyframe_insert(data_path="location",frame=tick)
        if tick in (0,6,12,18,23):
            observations[tick]=[evaluated_positions(obj) for arm,obj,marks in assets]
    move=[max(math.dist(a,b) for a,b in zip(observations[0][ai],observations[6][ai]))
          for ai in range(len(assets))]
    if len(move)!=2 or min(move)<.01:
        raise ValueError("ACTUAL_SKINNED_MESH_NOT_MOVING")
    glb=out/"original_synthetic_24frame_skinned.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb.resolve()),export_format="GLB",export_animations=True)
    if not glb.exists() or glb.stat().st_size<5000:
        raise ValueError("ACTUAL_NATIVE_GLB_NOT_CREATED")
    receipt={"schema":"scp.walk_w4d_native_24frame_smoke.v1",
             "status":"OBSERVED_NATIVE_SYNTHETIC_24FRAME_SKIN_MOTION_ONLY",
             "rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
             "glb_sha256":hashlib.sha256(glb.read_bytes()).hexdigest(),
             "frame_count":24,"fps_num":12,"fps_den":1,
             "actor_names":[x[0] for x in ACTORS],
             "native_skinned_vertex_displacement":move,
             "anatomy":"UNKNOWN_ARTIFICIAL_SINUSOIDAL_LOWER_BONE",
             "heel_sole_contact":"UNKNOWN_NOT_QUALIFIED",
             "full_body":"FAIL_ABSTRACT_LIMBS_ONLY",
             "visual_pixel":"UNKNOWN_NOT_RENDERED"}
    (out/"source_motion_receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("W4D_NATIVE_SYNTHETIC_GLTF_ANIMATED",json.dumps(receipt,sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    generate(p.parse_args().out)
