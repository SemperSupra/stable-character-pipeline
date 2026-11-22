"""Read-only genuine Blender 360-key CC0 first-edge causal/roundtrip observer.

Requires the same ephemeral saved original-only .blend as the independent shoe
full-clip witness. No asset upload, force/contact/identity/release inference.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from first_edge_oracle import evaluate, SEQ, need
from shoe360_native import sample_world_mesh
sys.path.insert(0,str(HERE.parent/"n03d-bi-cc0-shoe-60hz"))
from native import rest_groups, digest
sys.path.insert(0,str(HERE.parent/"r090-dressed"))
from real_retarget import pose_fingerprint, observed

SOURCE_BLOB="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61"

def source_root_delta(path):
    lines=Path(path).read_text(encoding="ascii").splitlines()
    need("MOTION" in lines,"SOURCE_BVH_MOTION_MISSING")
    ix=lines.index("MOTION")
    need(lines[ix+1].strip()=="Frames: 360","SOURCE_BVH_NOT_360")
    header=next((line.strip().split() for line in lines[:ix]
                 if line.strip().startswith("CHANNELS ")),None)
    need(header is not None and int(header[1])>=3,"SOURCE_ROOT_CHANNELS_MISSING")
    names=header[2:]
    need(len(names)==int(header[1]) and
         all(k in names for k in ("Xposition","Yposition","Zposition")),"SOURCE_ROOT_POSITIONS_MISSING")
    need(len(lines)==ix+3+360,"SOURCE_BVH_FRAME_COUNT")
    first=[[float(v) for v in lines[ix+3+j].split()] for j in (0,1)]
    inds=[names.index(k) for k in ("Xposition","Yposition","Zposition")]
    need(all(len(v)>max(inds) for v in first),"SOURCE_ROOT_FRAME_CHANNEL_SHORT")
    delta=[first[1][i]-first[0][i] for i in inds]
    need(all(math.isfinite(v) for v in delta),"SOURCE_ROOT_FIRST_EDGE_NONFINITE")
    return {"source_root_channel_delta_native_bvh_units":[round(v,9) for v in delta],
            "source_root_channel_norm_native_bvh_units":round(math.dist([0,0,0],delta),9),
            "native_units_not_calibrated_to_scene_m":True,
            "source_joint_fk_measured":False}

def point(rig,bone):
    p=rig.matrix_world @ rig.pose.bones[bone].head
    return [float(p.x),float(p.y),float(p.z)]

def main():
    p=argparse.ArgumentParser()
    for key in ("scene","sha","wardrobe","clock-report","fullclip","clip","out"):
        p.add_argument("--"+key,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    need(digest(a.scene)==a.sha,"SOURCE_REOPEN_NATIVE_SCENE_SHA")
    clock=json.loads(Path(a.clock_report).read_text())
    data=json.loads(Path(a.fullclip).read_text())
    need(clock.get("candidate_blend_sha256")==a.sha and
         clock.get("status")=="HOLD_NATIVE_CLOCK_EXPERIMENT" and
         clock.get("source_clip",{}).get("frames")==360 and
         clock.get("source_clip",{}).get("candidate_bvh_sha256")==digest(a.clip),
         "SOURCE_NATIVE_CLOCK_OR_CLIP_MISMATCH")
    need(data.get("schema")=="scp.r009.peer-original-native360-shoe-fullclip-v1" and
         data.get("exact_native_blend_sha256")==a.sha and
         data.get("source_60hz_frame_count")==360 and
         data.get("original_motion_git_blob_sha1")==SOURCE_BLOB and
         data.get("physical_contact_accepted") is False and
         data.get("mvp_accepted") is False,"SOURCE_NATIVE_SHOE_OR_RIGHTS_MISMATCH")
    sc=bpy.context.scene
    need((sc.render.fps,sc.render.fps_base,sc.frame_start,sc.frame_end)==(60,1.0,0,359),
         "SOURCE_NATIVE_360_CLOCK_MISSING")
    need(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL",
         "SOURCE_NOT_ORIGINAL_CC0")
    ward=json.loads(Path(a.wardrobe).read_text())
    need({p["name"] for p in ward["characters"]}=={"AsterOriginal","JuniperOriginal"},
         "SOURCE_PROTECTED_OR_MISSING_ACTOR")
    original={p["name"]:p for p in data["actors"]}
    need(set(original)=={"AsterOriginal","JuniperOriginal"},"SOURCE_SHOE_ACTORS_DIFFER")
    output=[]
    for person in ward["characters"]:
        name=person["name"]
        rig=bpy.data.objects.get(name+"_MPFBRig")
        body=bpy.data.objects.get(name+"_MPFBBody")
        garments=[g for g in person["garments"] if g["pack"]=="shoes01"]
        need(rig is not None and body is not None and len(garments)==1,
             "SOURCE_REAL_RIG_SKIN_OR_SHOE_MISSING")
        shoe=bpy.data.objects.get(garments[0]["native_object"])
        need(shoe is not None and any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers),
             "SOURCE_ACTUAL_CC0_SHOE_NOT_BOUND")
        sc.frame_set(0)
        rig.data.pose_position="REST"
        bpy.context.view_layer.update()
        regions=rest_groups(shoe,rig)
        xs=[float(v.co.x) for v in shoe.data.vertices]
        center=(min(xs)+max(xs))/2.0
        halves={"rest_local_x_positive":[i for i,x in enumerate(xs) if x>=center],
                "rest_local_x_negative":[i for i,x in enumerate(xs) if x<center]}
        side_ids={side:halves[r["partition"]] for side,r in regions.items()}
        need(set(side_ids)=={"L","R"} and all(len(x)>100 for x in side_ids.values()),
             "SOURCE_ACTUAL_SHOE_SIDE_ASSIGNMENT_FAILED")
        rig.data.pose_position="POSE"
        trace=[]
        for frame in SEQ:
            sc.frame_set(frame)
            bpy.context.view_layer.update()
            mesh=sample_world_mesh(shoe,side_ids,regions,frame)
            trace.append({
                "frame":frame,"shoe":mesh,
                "bones":{side:{"foot":point(rig,"foot."+side),
                               "toe":point(rig,"toe1-1."+side)} for side in ("L","R")},
                "pose_sha256":pose_fingerprint(rig),
                "body_sha256":observed(body)["sha256"],
            })
        baseline={side:original[name]["sides"][side]["rows"] for side in ("L","R")}
        m=evaluate(trace,baseline)
        output.append({"name":name,"sample_order":list(SEQ),"metrics":m,
                       "source_baseline_first_edge_m":{
                           side:{"heel_xy":[baseline[side][j]["heel_xy"] for j in (0,1)],
                                 "ball_xy":[baseline[side][j]["ball_xy"] for j in (0,1)]}
                           for side in ("L","R")},
                       "readback_digest":{str(frame):{
                           "pose_sha256":trace[k]["pose_sha256"],
                           "body_sha256":trace[k]["body_sha256"]}
                           for k,frame in enumerate(SEQ) if k in (0,1,2,3,5,6)}})
    report={
        "schema":"scp.r009.peer-original-native360-first-edge-replay-v1",
        "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
        "exact_native_blend_sha256":a.sha,
        "fullclip_observer_sha256":digest(a.fullclip),
        "source_root":source_root_delta(a.clip),
        "actors":output,
        "physical_contact_accepted":False,
        "anatomical_source_fk_accepted":False,
        "ground_reaction_force_measured":False,
        "protected_likeness_used":False,
        "mvp_accepted":False,
        "status":"HOLD",
    }
    Path(a.out).write_text(json.dumps(report,sort_keys=True,allow_nan=False)+"\n")
    print("R009_FIRST_EDGE_REPLAY_HOLD",json.dumps({
        "source_root":report["source_root"],
        "actors":{v["name"]:v["metrics"] for v in output},
        "status":"HOLD"},sort_keys=True),flush=True)

if __name__=="__main__":
    main()
