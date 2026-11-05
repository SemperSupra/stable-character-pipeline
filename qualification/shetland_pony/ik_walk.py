"""Blender-native 3-link equine forearm/stifle-aware IK gait experiment.

Tracks ankle (lower bone's tail) from deterministic source-original footpaths,
then visually bakes evaluated IK pose to FK keyframes for GLB interoperability.
No source horses, photo references, dataset or third-party motion included.
"""
import bpy
import math
from pathlib import Path
import footpaths
from equine_anatomy import LIMITS,TWIST_MAX_DEG

def animate_ik_walk(arm, out=None):
    sc = bpy.context.scene
    sc.frame_start=1
    sc.frame_end=footpaths.CYCLE_FRAMES
    sc.render.fps=24
    for pb in arm.pose.bones:
        pb.rotation_mode="XYZ"
    targets={}
    poles={}
    for foot in footpaths.FOOT_CONTACT_PHASE:
        target=bpy.data.objects.new("IK_TARGET_"+foot,None)
        bpy.context.collection.objects.link(target)
        target.hide_render=True
        target.empty_display_type="SPHERE"
        target.empty_display_size=0.025
        targets[foot]=target
        lower=arm.pose.bones[foot+"_lower"]
        ik=lower.constraints.new("IK")
        ik.name="FOOTPATH_IK_"+foot
        ik.target=target
        ik.chain_count=3
        ik.use_stretch=False
        ik.iterations=225
        ik.weight=1.0
        prefix,side=foot.split("_")
        intermediate="forearm" if prefix=="front" else "stifle"
        chain=(arm.pose.bones[foot+"_upper"],arm.pose.bones[foot+"_"+intermediate],lower)
        pole=bpy.data.objects.new("IK_POLE_"+foot,None)
        bpy.context.collection.objects.link(pole)
        pole.location=( (.40 if prefix=="front" else -.48) + (-.35 if prefix=="front" else .35),
                        -.20 if side=="L" else .20,.50 )
        pole.hide_render=True
        pole.empty_display_size=.02
        poles[foot]=pole
        ik.pole_target=pole
        ik.pole_angle=0.
        # Every driven joint receives conservative local-axis hard stops.
        # These are provisional ENGINEERING bounds, not clinical equine ROM.
        labels=("upper",intermediate,"lower")
        for bone,label in zip(chain,labels):
            lim=LIMITS[label]
            bone.use_ik_limit_x=True
            bone.ik_min_x=math.radians(lim["x"][0])
            bone.ik_max_x=math.radians(lim["x"][1])
            bone.use_ik_limit_y=True
            bone.ik_min_y=-math.radians(TWIST_MAX_DEG)
            bone.ik_max_y=math.radians(TWIST_MAX_DEG)
            bone.use_ik_limit_z=True
            bone.ik_min_z=math.radians(lim["z"][0])
            bone.ik_max_z=math.radians(lim["z"][1])

    traces={}
    for frame in range(1,footpaths.CYCLE_FRAMES+1):
        sc.frame_set(frame)
        world_root=footpaths.target(frame, "hind_L").root_x
        arm.location.x=world_root
        arm.keyframe_insert(data_path="location",frame=frame,group="root_world_motion")
        traces[str(frame)]={}
        for foot,target in targets.items():
            p=footpaths.target(frame,foot)
            target.location=(p.ankle_x,p.ankle_y,p.ankle_z)
            target.keyframe_insert(data_path="location",frame=frame,group="IK_targets")
            traces[str(frame)][foot]={"ankle_target_world_m":[round(p.ankle_x,6),round(p.ankle_y,6),round(p.ankle_z,6)],
                                     "contact_state":p.state}
        # Secondary tail movement is subtle and follows gait phase, not contact or emotion.
        tail=arm.pose.bones["tail_2"]
        tail.rotation_euler[0]=0.10*math.sin(math.tau*(frame-1)/footpaths.CYCLE_FRAMES)
        tail.keyframe_insert(data_path="rotation_euler",frame=frame,group=tail.name)

    sc.frame_set(1)
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode!="OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    # Critical: glTF cannot reproduce Blender IK constraints. Bake evaluated
    # visual bone motion to ordinary FK tracks BEFORE GLB export.
    bpy.ops.nla.bake(frame_start=1,frame_end=footpaths.CYCLE_FRAMES,
                    step=1,only_selected=True,visual_keying=True,
                    clear_constraints=True,use_current_action=True,
                    bake_types={"POSE"})
    bpy.ops.object.mode_set(mode="OBJECT")
    for obj in list(targets.values())+list(poles.values()):
        bpy.data.objects.remove(obj,do_unlink=True)
    sc.frame_set(1)
    if out:
        import json
        receipt={"schema":"equine.ik.plan.v1",
            "gait":"walk","rig":"30-joint source-original equine procedural",
            "contact_state":"PLANNED_SOURCE_TARGETS_NOT_EVALUATED",
            "ik":"three-link pole-aware chain with temporary provisional IK-axis limits, visually baked",
            "root_translation_m":footpaths.STRIDE_M,
            "anatomical_joints":30,
            "limits":"engineering-only; independent native 48f world-space ROM observer required",
            "duty_factor":footpaths.DUTY_FACTOR,
            "minimum_planned_swing_height_m":footpaths.SWING_HEIGHT_M,
            "frames":traces}
        Path(out).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    return traces
