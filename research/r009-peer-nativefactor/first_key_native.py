"""R009 source→native first-key factor witness: original-only, read-only Blender.

True saved/reopened 360@60Hz Diffeomorphic action, pinned BVH source and CC0 rigs.
Exposes original source 120→121→122 FK versus native world bone heads 0→1→2
and actual action FCurve first/second-edge jumps. No anatomical acceptance.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"r009-peer-native60"))
from native_action import action_fcurves, keyframe_receipt
sys.path.insert(0,str(HERE.parent/"r090-dressed"))
from real_retarget import digest
sys.path.insert(0,str(HERE.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh, fk

JOINTS={"L":("LeftAnkle","LeftToe"),"R":("RightAnkle","RightToe")}
NATIVE={"L":("foot.L","toe1-1.L"),"R":("foot.R","toe1-1.R")}

def require(ok,reason):
    if not ok:raise ValueError(reason)

def vec(v):
    require(len(v)==3 and all(math.isfinite(float(x)) for x in v),
            "NONFINITE_WORLD_BONE")
    return [float(x) for x in v]

def step_metric(seq, dt=1/60.0):
    require(len(seq)>=3 and math.isfinite(dt) and dt>0,"INVALID_FIRST_KEY_SEQUENCE")
    a,b,c=(vec(q) for q in seq[:3])
    a0=[b[i]-a[i] for i in range(3)]
    a1=[c[i]-b[i] for i in range(3)]
    return {"first_delta_xyz_m":[round(q,9) for q in a0],
            "next_delta_xyz_m":[round(q,9) for q in a1],
            "first_3d_speed_mps":round(math.dist(a,b)/dt,6),
            "next_3d_speed_mps":round(math.dist(b,c)/dt,6),
            "first_xy_speed_mps":round(math.hypot(a0[0],a0[1])/dt,6),
            "next_xy_speed_mps":round(math.hypot(a1[0],a1[1])/dt,6)}

def summarize_channels(curves):
    summary=[]
    for curve in curves:
        points={int(round(float(k.co.x))):float(k.co.y)
                for k in curve.keyframe_points
                if abs(float(k.co.x)-round(float(k.co.x)))<1e-5 and
                int(round(float(k.co.x))) in (0,1,2)}
        if len(points)!=3:
            continue
        d01=points[1]-points[0]
        d12=points[2]-points[1]
        require(all(math.isfinite(t) for t in (d01,d12)),
                "SOURCE_ACTION_NONFINITE_FIRST_KEYS")
        summary.append({"path":str(curve.data_path),
                        "array_index":int(curve.array_index),
                        "first_abs_key_delta":round(abs(d01),9),
                        "next_abs_key_delta":round(abs(d12),9)})
    require(len(summary)>=10,"SOURCE_ACTION_FIRST_KEYS_INSUFFICIENT")
    order=sorted(summary,key=lambda x:-x["first_abs_key_delta"])
    return {"inspected_animated_and_constant_channels":len(summary),
            "top_12_first_key_channel_deltas":order[:12],
            "first_key_nonzero_channels":sum(x["first_abs_key_delta"]>1e-6 for x in summary),
            "next_key_nonzero_channels":sum(x["next_abs_key_delta"]>1e-6 for x in summary),
            "values_mixed_units_no_raw_norm_conclusion":True}

def source_series(clip):
    data=parse_bvh(Path(clip).read_bytes())
    require(data["count"]==360 and abs(data["frame_time"]-1/60)<1e-5,
            "AUTHENTIC_SOURCE_CLIP_360_AT_60_REQUIRED")
    world=[fk(data,i) for i in range(3)]
    return {side:{native_name:step_metric([
              [float(q[src_name][j])*0.01 for j in range(3)] for q in world])
             for src_name,native_name in zip(JOINTS[side],NATIVE[side])}
            for side in ("L","R")}

def native_series(rig):
    joints={}
    for side in ("L","R"):
        joints[side]={}
        for name in NATIVE[side]:
            require(name in rig.pose.bones,"NATIVE_RIG_FOOT_OR_TOE_MISSING")
            points=[]
            for frame in (0,1,2):
                bpy.context.scene.frame_set(frame)
                bpy.context.view_layer.update()
                bone=rig.pose.bones[name]
                points.append(vec(rig.matrix_world@bone.head))
            joints[side][name]=step_metric(points)
    return joints

def main():
    ap=argparse.ArgumentParser()
    for name in ("scene","sha","clock-report","clip","out"):
        ap.add_argument("--"+name,required=True)
    args=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
    require(digest(args.scene)==args.sha,"NATIVE_SCENE_SHA_CHANGED")
    rec=json.loads(Path(args.clock_report).read_text())
    require(rec.get("candidate_blend_sha256")==args.sha and
            rec.get("status")=="HOLD_NATIVE_CLOCK_EXPERIMENT" and
            rec.get("source_clip",{}).get("candidate_bvh_sha256")==digest(args.clip) and
            rec.get("source_clip",{}).get("source_frames")==[120,479],
            "NATIVE_SOURCE_CORRESPONDENCE_NOT_VERIFIED")
    sc=bpy.context.scene
    require((sc.render.fps,sc.render.fps_base,sc.frame_start,sc.frame_end)==(60,1.0,0,359) and
            sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
            sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL",
            "NATIVE_RIG_CLOCK_OR_RIGHTS")
    src=source_series(args.clip)
    actors=[]
    for name in ("AsterOriginal","JuniperOriginal"):
        rig=bpy.data.objects.get(name+"_MPFBRig")
        require(rig is not None and len(rig.data.bones)==163,
                "NATIVE_RIG_NOT_AUTHENTIC_MPF163")
        keys=keyframe_receipt(rig)
        require(keys["distinct_native_key_times"]==360 and
                keys["first_key_time"]==0 and keys["last_key_time"]==359,
                "NATIVE_ACTION_DECIMATED")
        target=native_series(rig)
        comparisons={}
        for side in ("L","R"):
            comparisons[side]={}
            for native_name in NATIVE[side]:
                original=src[side][native_name]
                actual=target[side][native_name]
                comparisons[side][native_name]={
                  "original_source":original,"evaluated_native":actual,
                  "first_speed_ratio_native_over_source":
                      round(actual["first_3d_speed_mps"]/original["first_3d_speed_mps"],6)
                      if original["first_3d_speed_mps"]>1e-9 else None,
                  "first_key_native_above_10mps":actual["first_3d_speed_mps"]>10.,
                  "source_native_anatomical_semantics_accepted":False}
        actors.append({"actor":name,"original_source_clip_frames":[120,121,122],
                       "native_action_frames":[0,1,2],"key_receipt":keys,
                       "comparison":comparisons,
                       "first_key_action_channels":summarize_channels(action_fcurves(rig))})
    out={"schema":"scp.r009.peer-source-native-firstkey-factor-v1",
         "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
         "exact_scene_sha256":args.sha,
         "source_clip_sha256":digest(args.clip),
         "source_100style_bvh_world_axes":"Y-up, centimetres",
         "target_blender_world_axes":"Z-up, metres",
         "source_to_native_anatomical_mapping_accepted":False,
         "source_fk_component_rotation_mapping_proven":False,
         "retarget_initial_key_causality_proven":False,
         "actual_shoe_contact_accepted":False,
         "mvp_accepted":False,"status":"HOLD","actors":actors}
    Path(args.out).write_text(json.dumps(out,sort_keys=True,allow_nan=False)+"\n")
    print("R009_SOURCE_NATIVE_FIRSTKEY_FACTOR_HOLD",
          json.dumps({"actors":[{"actor":a["actor"],"comparison":a["comparison"],
                                   "channel_summary":a["first_key_action_channels"]}
                                  for a in actors],"status":"HOLD"},sort_keys=True),flush=True)

if __name__=="__main__":main()
