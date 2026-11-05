"""Bounded circular rotation-mean on gait pose keys (source-original).

This is a corrective experiment to address 23.27-degree front carpus snap,
NOT a proof of hoof-ground contact. Recompute independent GLB angle and
foot proxies after modifying baked keys; reject if either worsens materially.
"""
import math

KERNEL=(1,2,3,2,1)

def circular_mean(vals,weights=KERNEL):
    if len(vals)!=len(weights) or not vals:
        raise ValueError("wrong window")
    sx=sum(math.sin(v)*w for v,w in zip(vals,weights))
    cx=sum(math.cos(v)*w for v,w in zip(vals,weights))
    if abs(sx)+abs(cx)<1e-10:raise ValueError("ambiguous cyclic mean")
    return math.atan2(sx,cx)

def smooth_euler_cycle(rotations):
    if len(rotations)!=48:
        raise ValueError("expect exact native 48-frame gait cycle")
    if any(len(r)!=3 or any(not math.isfinite(x) for x in r) for r in rotations):
        raise ValueError("invalid source Euler triple")
    out=[]
    for i in range(48):
        result=[]
        for axis in range(3):
            angles=[rotations[(i+j-2)%48][axis] for j in range(5)]
            result.append(circular_mean(angles))
        out.append(tuple(result))
    return out

def smooth_baked_pose(arm,sc,parts):
    import bpy
    if not all(arm.pose.bones.get(name) is not None for name in parts):
        raise ValueError("missing exact source joint to filter")
    for name in parts:
        rotations=[]
        for frame in range(1,49):
            sc.frame_set(frame)
            rotations.append(tuple(float(v) for v in arm.pose.bones[name].rotation_euler))
        filtered=smooth_euler_cycle(rotations)
        for frame,rotation in enumerate(filtered,1):
            sc.frame_set(frame)
            bone=arm.pose.bones[name]
            bone.rotation_euler=rotation
            bone.keyframe_insert(data_path="rotation_euler",frame=frame,group=name)
    sc.frame_set(1)
    return {"schema":"equine.circular_ik_filter.v1","bones":list(parts),"frames":48,
            "kernel":list(KERNEL),"qualification":"NEEDS_INDEPENDENT_30JOINT_ROM_AND_HOOF_SCREEN"}
