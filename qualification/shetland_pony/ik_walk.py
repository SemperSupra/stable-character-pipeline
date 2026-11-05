"""Blender-native 2-link inverse-kinematic hoof target experiment.

Tracks ankle (lower bone's tail) from deterministic source-original footpaths,
then visually bakes evaluated IK pose to FK keyframes for GLB interoperability.
No source horses, photo references, dataset or third-party motion included.
"""
import bpy
import math
from pathlib import Path
import footpaths

def animate_ik_walk(arm, out=None):
    sc = bpy.context.scene
    sc.frame_start=1
    sc.frame_end=footpaths.CYCLE_FRAMES
    sc.render.fps=24
    for pb in arm.pose.bones:
        pb.rotation_mode="XYZ"
    targets={}
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
        ik.chain_count=2
        ik.use_stretch=False
        ik.iterations=150
        ik.weight=1.0

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
    for obj in targets.values():
        bpy.data.objects.remove(obj,do_unlink=True)
    sc.frame_set(1)
    if out:
        import json
        receipt={"schema":"equine.ik.plan.v1",
            "gait":"walk","rig":"26-joint source-original procedural Shetland",
            "contact_state":"PLANNED_SOURCE_TARGETS_NOT_EVALUATED",
            "ik":"two-link lower-bone-tail target; visually baked",
            "root_translation_m":footpaths.STRIDE_M,
            "duty_factor":footpaths.DUTY_FACTOR,
            "minimum_planned_swing_height_m":footpaths.SWING_HEIGHT_M,
            "frames":traces}
        Path(out).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    return traces
