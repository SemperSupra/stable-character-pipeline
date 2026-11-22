"""R009 independent original-CC0 360-key/60Hz native Blender action experiment.

Derives the authentic 100STYLE 360-frame BVH subset and performs a NEW pinned
Diffeomorphic retarget on the original (pre-R090) MPFB/CC0 Blender scene, AFTER
setting the scene clock to 60fps. Readback verifies actual FCurves, timebase,
source tail motion and saved native pose/skin. This does not prove semantics,
anatomy, kinetics, contact, identity, naturalness or MVP.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
from clock_contract import validate
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"r090-dressed"))
from real_retarget import source_clip, digest, observed, pose_fingerprint, PLUGIN_COMMIT


def require(ok,code):
    if not ok:
        raise RuntimeError(code)


def action_fcurves(rig):
    action=rig.animation_data.action
    curves=[]
    # Blender legacy Action and current layered/slotted Actions both occur.
    try:
        curves=list(action.fcurves)
    except (AttributeError,RuntimeError,TypeError):
        pass
    if curves:
        return curves
    slot=getattr(rig.animation_data,"action_slot",None)
    for layer in action.layers:
        for strip in layer.strips:
            try:
                cb=strip.channelbag(slot) if slot is not None else None
                if cb:
                    curves.extend(list(cb.fcurves))
            except (AttributeError,RuntimeError,TypeError):
                pass
            if not curves:
                for bag in getattr(strip,"channelbags",[]):
                    curves.extend(list(bag.fcurves))
    require(len(curves)>0,"NATIVE_ACTION_NO_INSPECTABLE_FCURVES")
    return curves


def keyframe_receipt(rig):
    curves=action_fcurves(rig)
    all_times=set()
    animated_counts=[]
    for curve in curves:
        frames=[float(k.co.x) for k in curve.keyframe_points]
        require(frames and all(math.isfinite(t) for t in frames),"NATIVE_FCURVE_NAN_OR_EMPTY")
        all_times.update(round(t,6) for t in frames)
        if len(frames)>1:
            animated_counts.append(len(frames))
    times=sorted(all_times)
    validate(times,60.0)  # Independent source↔target 360-key hostile oracle.
    require(animated_counts and min(animated_counts)>=350,
            "NATIVE_ACTION_CURVE_DECIMATION_PERSISTS")
    return {
        "fcurve_count":len(curves),
        "animated_fcurve_count":len(animated_counts),
        "min_animated_curve_keys":min(animated_counts),
        "max_animated_curve_keys":max(animated_counts),
        "distinct_native_key_times":len(times),
        "first_key_time":times[0],
        "last_key_time":times[-1],
    }


def pfoot(rig,side):
    obj=rig.matrix_world @ rig.pose.bones["foot."+side].head
    return (float(obj.x),float(obj.y),float(obj.z))


def trace_actor(rig,body,first):
    out=[]
    left_tail=[]
    right_tail=[]
    for idx in (0,120,240,355,356,357,358,359):
        bpy.context.scene.frame_set(first+idx)
        bpy.context.view_layer.update()
        out.append({"source_index":idx,
                    "target_frame":first+idx,
                    "pose_sha256":pose_fingerprint(rig),
                    "body":observed(body)})
        if idx>=355:
            left_tail.append(pfoot(rig,"L"))
            right_tail.append(pfoot(rig,"R"))
    left=sum(math.dist(left_tail[i],left_tail[i-1]) for i in range(1,len(left_tail)))
    right=sum(math.dist(right_tail[i],right_tail[i-1]) for i in range(1,len(right_tail)))
    require(left>0.0001,"NATIVE_360_ACTION_LEFT_FOOT_TAIL_FROZEN")
    return out, left, right


def build(args):
    require(digest(args.scene)==args.sha,"SOURCE_SCENE_SHA_MISMATCH")
    sc=bpy.context.scene
    require(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
            sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL",
            "PROTECTED_ASSET_OR_WRONG_SOURCE")
    require((sc.frame_start,sc.frame_end,sc.render.fps)==(0,71,12),"EXPECTED_PRE_RETARGET_SOURCE_CLOCK")
    import addon_utils
    module="bl_ext.user_default.retarget_bvh"
    addon_utils.enable(module,default_set=False,persistent=False)
    require(addon_utils.check(module)[1],"PINNED_VENDOR_ADDON_NOT_ENABLED")
    from importlib import import_module
    vendor=import_module(module)
    vendor.setSilentMode(True)
    from bl_ext.user_default.retarget_bvh.bsettings import BD
    from bl_ext.user_default.retarget_bvh.utils import mcpRna
    require(hasattr(bpy.ops.mcp,"load_and_retarget"),"VENDOR_OPERATOR_MISSING")
    source=source_clip(args.source,args.clip)
    require(source["frames"]==360 and abs(source["source_fps"]-60.0)<0.01,"SOURCE_NOT_360_AT_60")
    # This is the decisive A/B against legacy R090: change clock BEFORE
    # retargeting; do not subframe-interpolate a 12fps action afterwards.
    sc.render.fps=60
    sc.render.fps_base=1.0
    sc.frame_start=0
    sc.frame_end=359
    actors=[]
    for name in ("AsterOriginal","JuniperOriginal"):
        rig=bpy.data.objects.get(name+"_MPFBRig")
        body=bpy.data.objects.get(name+"_MPFBBody")
        require(rig is not None and body is not None and len(rig.data.bones)==163,
                "ORIGINAL_MPF163_CHARACTER_MISSING")
        bpy.ops.object.select_all(action="DESELECT")
        rig.hide_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active=rig
        BD.ensureInited(sc)
        BD.ensureTargetInited(sc)
        mcpRna(sc).TargetRig="MakeHuman"
        mcpRna(sc).TargetTPose="Default"
        prior=rig.animation_data.action if rig.animation_data else None
        done=bpy.ops.mcp.load_and_retarget(
            filepath=str(Path(args.clip).resolve()),
            useAllFrames=False,startFrame=1,endFrame=360,
            useNLA=False,useBendPositive=False,useAutoTarget=False,
            useDefaultSS=True,useSimplify=False,useTimeScale=False)
        require("FINISHED" in done,"VENDOR_RETARGET_NOT_FINISHED")
        require(vendor.getErrorMessage().strip()=="BVH file(s) retargeted",
                "VENDOR_REPORTED_ERROR_"+name+"_"+vendor.getErrorMessage())
        require(rig.animation_data is not None and rig.animation_data.action is not None and
                rig.animation_data.action != prior,"REUSED_OR_ABSENT_NATIVE_ACTION")
        action=rig.animation_data.action
        first,last=tuple(float(t) for t in action.frame_range)
        require(abs((last-first)-359)<1e-4 and abs((last-first)/60.0-359/60.0)<1e-7,
                "NATIVE_ACTION_60HZ_DURATION_OR_TAIL_TRUNCATED")
        keys=keyframe_receipt(rig)
        first_int=int(round(first))
        samples,left,right=trace_actor(rig,body,first_int)
        require(len({q["pose_sha256"] for q in samples})>=7,
                "NATIVE_POSE_NOT_MOVING_ALL_SAMPLES")
        actors.append({"name":name,"action":action.name,"frame_range":[first,last],
                       "keys":keys,"sampled_native_pose_skin":samples,
                       "left_tail_world_path_m":round(left,9),
                       "right_tail_world_path_m":round(right,9),
                       "retargeted_motion_semantics_accepted":False})
    require(abs(actors[0]["frame_range"][0]-actors[1]["frame_range"][0])<1e-5,
            "TWO_ACTOR_CLOCK_ORIGIN_DIVERGENCE")
    sc.frame_start=int(round(actors[0]["frame_range"][0]))
    sc.frame_end=int(round(actors[0]["frame_range"][1]))
    output=Path(args.out)
    candidate=output.with_suffix(".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate.resolve()))
    report={"schema":"scp.r009.peer-true-native60-v1",
            "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
            "original_scene_sha256":args.sha,
            "candidate_blend_sha256":digest(candidate),
            "source_clip":source,
            "plugin_git_commit":PLUGIN_COMMIT,
            "native_fps":sc.render.fps,"native_fps_base":sc.render.fps_base,
            "actors":actors,
            "physical_contact_accepted":False,
            "anatomical_semantics_accepted":False,
            "protected_likeness_used":False,
            "mvp_accepted":False,
            "status":"HOLD_NATIVE_CLOCK_EXPERIMENT"}
    output.write_text(json.dumps(report,sort_keys=True,allow_nan=False)+"\n")
    print("R009_TRUE_NATIVE_360_ACTION_DIAGNOSTIC",json.dumps({
        "candidate_blend_sha256":report["candidate_blend_sha256"],
        "source_frames":source["frames"],"actors":[{
            "name":a["name"],"keys":a["keys"],
            "left_tail_world_path_m":a["left_tail_world_path_m"],
            "right_tail_world_path_m":a["right_tail_world_path_m"]} for a in actors],
        "status":report["status"]},sort_keys=True),flush=True)


def verify(args):
    p=Path(args.out)
    r=json.loads(p.read_text())
    scene=p.with_suffix(".blend")
    require(digest(scene)==r["candidate_blend_sha256"],"NATIVE_SCENE_REOPEN_SHA_CHANGED")
    sc=bpy.context.scene
    require(sc.render.fps==60 and sc.render.fps_base==1.0,"REOPEN_60HZ_CLOCK_LOST")
    for a in r["actors"]:
        rig=bpy.data.objects.get(a["name"]+"_MPFBRig")
        body=bpy.data.objects.get(a["name"]+"_MPFBBody")
        require(rig and body and rig.animation_data and rig.animation_data.action,
                "REOPEN_NATIVE_RIG_MISSING")
        require(keyframe_receipt(rig)==a["keys"],"REOPEN_CHANGED_ACTION_KEYFRAMES")
        for sample in a["sampled_native_pose_skin"]:
            sc.frame_set(sample["target_frame"])
            bpy.context.view_layer.update()
            require(pose_fingerprint(rig)==sample["pose_sha256"],
                    "REOPEN_POSE_CHANGED_"+a["name"])
            require(observed(body)==sample["body"],
                    "REOPEN_SKIN_CHANGED_"+a["name"])
    print("R009_TRUE_NATIVE_360_REOPEN_HOLD",r["candidate_blend_sha256"],flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--stage",choices=("build","verify"),required=True)
    for n in ("scene","sha","source","clip","out"):
        p.add_argument("--"+n,default="")
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    if a.stage=="build":
        build(a)
    else:
        verify(a)
