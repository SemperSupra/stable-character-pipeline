"""W5A: actual evaluated Blender local joint poses -> source-pinned Go ROM V1 input.

A synthetic numeric contract only, no ISB human joint frame or IK target proof.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import bpy
from rebind_after_import import evaluated_local_x

def run(folder):
    folder=Path(folder)
    original=folder/"original_imported_rebound_limits.blend"
    prior=json.loads((folder/"restoration_observation.json").read_text())
    if hashlib.sha256(original.read_bytes()).hexdigest()!=prior["restored_blend_sha256"]:
        raise ValueError("NATIVE_REBOUND_BINARY_SHA_CHANGED")
    bpy.ops.wm.open_mainfile(filepath=str(original.resolve()))
    rigs=[x for x in bpy.data.objects if x.type=="ARMATURE"]
    if len(rigs)!=1:
        raise ValueError("UNQUALIFIED_RIG_TOPOLOGY")
    rig=rigs[0];bone=rig.pose.bones["OriginalLower"]
    if bone.parent is None or bone.parent.name!="OriginalUpper":
        raise ValueError("JOINT_PARENT_WRONG")
    props=[c for c in bone.constraints if c.type=="LIMIT_ROTATION"]
    if len(props)!=1 or props[0].owner_space!="LOCAL" or not bone.use_ik_limit_x:
        raise ValueError("RESTORED_OPERATIVE_LIMITS_MISSING")
    poses=[]
    for tick,angle in enumerate([0,.2,.4,.6,1.15]):
        bpy.context.scene.frame_set(tick)
        bone.rotation_mode="XYZ";bone.rotation_euler=(angle,0,0)
        output=evaluated_local_x(rig,"OriginalLower")
        if not math.isfinite(output):
            raise ValueError("EVALUATED_ANGLE_NOT_FINITE")
        poses.append({"tick":tick,"q":{"OriginalLower":output}})
    if poses[-1]["q"]["OriginalLower"]>.77 or poses[-1]["q"]["OriginalLower"]<.72:
        raise ValueError("ACTUAL_LAST_POSE_NOT_CONSTRAINED")
    h=hashlib.sha256(original.read_bytes()).hexdigest()
    joint={"id":"OriginalLower","kind":"revolute","unit":"rad",
           "frame":"PARENT_LOCAL_TEST_ONLY","provenance":"SYNTHETIC_TEST_ONLY",
           "hard_min":-.75,"hard_max":.75,"soft_min":-.7,"soft_max":.7,
           "max_velocity":8.0,"max_acceleration":100.0,"max_jerk":1000.0}
    specimen={"schema":"scp.rom.v1_input","rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
              "source_sha256":h,"morphology":"synthetic_fixture",
              "context":"synthetic local x armature unloaded",
              "rate_num":12,"rate_den":1,"joints":[joint],"frames":poses}
    (folder/"w5a_evaluated_poses_go.json").write_text(json.dumps(specimen,sort_keys=True,indent=2)+"\n")
    hostile=json.loads(json.dumps(specimen))
    hostile["frames"][-1]["q"]["OriginalLower"]=1.15
    (folder/"w5a_unconstrained_bad_go.json").write_text(json.dumps(hostile,sort_keys=True,indent=2)+"\n")
    expected={"schema":"scp.rom.w5a_evaluated_joint_bridge.v1",
              "status":"OBSERVED_ACTUAL_NATIVE_JOINT_TO_GO_ONLY",
              "source_sha256":h,"bound_rad":[-.75,.75],
              "actual_observed_evaluated_joint_rad":[s["q"]["OriginalLower"] for s in poses],
              "malicious_last_observation_rad":1.15,
              "anatomy":"UNKNOWN_NOT_HUMAN_JCS",
              "kinematic_target_ik":"UNKNOWN_NO_TARGET",
              "actual_visual_quality":"UNKNOWN_NOT_RENDERED"}
    (folder/"w5a_source_observation.json").write_text(json.dumps(expected,sort_keys=True,indent=2)+"\n")
    print("W5A_ACTUAL_NATIVE_BONE_LOCAL_EVALUATED",json.dumps(expected,sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);run(p.parse_args().out)
