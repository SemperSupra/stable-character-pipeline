"""N03D-BG source world bone matrix -> Blender bind space, no approximate per-bone quats.

Fitted rigid 3D source/target rest landmark similarity (5 TRAIN, 4 HELDOUT)
and fixed axis swap control, 360 true source/target posed matrices each.
This is source GLB same body, not Na/Al private and not physical gait acceptance.
"""
import argparse,hashlib,json,math,statistics,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"n03d-bf-three-to-blender"))
import native_bridge as bf

TRAIN=("Hips","LeftHip","RightHip","LeftKnee","RightKnee")
HOLD=("LeftAnkle","RightAnkle","LeftToe","RightToe")
ORDER=("Hips","LeftHip","RightHip","LeftKnee","RightKnee",
       "LeftAnkle","RightAnkle","LeftToe","RightToe")
def need(ok,why):
    if not ok:raise ValueError(why)
def mat(values):
    need(type(values)==list and len(values)==16 and
         all(type(x) in (float,int) and math.isfinite(x) for x in values),"INVALID_NATIVE_THREE_MATRIX")
    return Matrix(tuple(tuple(values[4*c+r] for c in range(4)) for r in range(4)))
def mjson(matrix):
    return [round(float(matrix[r][c]),9) for c in range(4) for r in range(4)]
def sim3(xs,ys):
    x=np.array(xs,float);y=np.array(ys,float)
    need(x.shape==y.shape and x.shape[1]==3 and x.shape[0]>=4,"NONIDENTIFIABLE_SIM3")
    need(np.all(np.isfinite(x)) and np.all(np.isfinite(y)),"NAN_IN_REST_LANDMARKS")
    mx=x.mean(axis=0);my=y.mean(axis=0)
    dx=x-mx;dy=y-my
    need(float(np.linalg.svd(dx,compute_uv=False)[-1])>1e-4,
         "DEGENERATE_SOURCE_REST_LANDMARKS")
    u,d,vt=np.linalg.svd(dx.T@dy)
    R=vt.T@np.diag([1.,1.,np.linalg.det(vt.T@u.T)])@u.T
    denom=float(np.square(dx).sum())
    scale=float((dy*(dx@R.T)).sum()/denom)
    need(.25<scale<4 and abs(np.linalg.det(R)-1)<1e-5,"SIM3_REFLECTION_OR_SCALE")
    t=my-scale*R@mx
    A=Matrix(((float(scale*R[0,0]),float(scale*R[0,1]),float(scale*R[0,2]),float(t[0])),
              (float(scale*R[1,0]),float(scale*R[1,1]),float(scale*R[1,2]),float(t[1])),
              (float(scale*R[2,0]),float(scale*R[2,1]),float(scale*R[2,2]),float(t[2])),
              (0,0,0,1)))
    return A,scale,R
def points_rms(A,source,target,keys):
    err=[(A@source[k].translation-target[k].translation).length for k in keys]
    return {"rms_m":round(math.sqrt(sum(z*z for z in err)/len(err)),6),
            "max_m":round(max(err),6),"by_joint_m":{key:round(error,6) for key,error in zip(keys,err)}}
def compare(records,phases):
    speeds=[60*math.dist(records[i]["xy"],records[i-1]["xy"])
            for i in range(1,len(records))]
    lows=[r["min_z"] for r in records]
    floor=min(lows)
    nonswing=[speeds[i-1] for i in range(1,len(records)) if
              phases[i]!="SWING" and phases[i-1]!="SWING"]
    near=[speeds[i-1] for i in range(1,len(records)) if
          lows[i]<floor+.012 and lows[i-1]<floor+.012]
    need(len(speeds)==359 and len(nonswing)>20,"NO_SOURCE_NONS WING_EVIDENCE".replace(" ",""))
    return {"samples":len(records),"stable_material_count":records[0]["count"],
            "fullclip_p50_xy_speed_mps":round(statistics.median(speeds),6),
            "nonswing_p50_xy_speed_mps":round(statistics.median(nonswing),6),
            "nonswing_adjacent_pairs":len(nonswing),
            "near_self_low_p50_xy_speed_mps":round(statistics.median(near),6) if near else None,
            "near_self_low_adjacent_pairs":len(near),
            "own_min_z_m":round(floor,6),
            "own_max_z_m":round(max(lows),6),
            "source_nonswing_is_not_force_verified":True,
            "actual_sole_and_ground_unverified":True}
def main():
    a=argparse.ArgumentParser()
    for k in ("rig","source","model","out"):a.add_argument("--"+k,required=True)
    args=a.parse_args(sys.argv[sys.argv.index("--")+1:])
    need(args.rig in bf.FILES,"RIG_NOT_PINNED")
    model=Path(args.model).read_bytes()
    need(bf.blob(model)==bf.FILES[args.rig][1],"UNTRUSTED_SOURCE_MODEL_BLOB")
    doc=json.loads(Path(args.source).read_text())
    need(doc.get("schema")=="scp.n03d-bg.source-world-pose-60hz-v1" and
         doc.get("original_source_commit")==bf.PIN and
         doc.get("source_glb_model")==bf.FILES[args.rig][0] and
         doc.get("public_original_cc0_only") is True and
         doc.get("source_grf_measured") is False and
         doc.get("physical_gait_accepted") is False and
         doc.get("mvp_accepted") is False and
         len(doc.get("frames",[]))==360 and
         doc.get("genuine_realtime_three_frames_60hz")==360 and
         doc.get("original_100style_motion_identical") is False,
         "THREE_WORLD_SOURCE_PROVENANCE")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.model).resolve()))
    riglist=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    need(len(riglist)==1,"ACTUAL_BLENDER_ARMATURE")
    rig=riglist[0]
    if bf.FILES[args.rig][2]:need(len(rig.data.bones)==bf.FILES[args.rig][2],"WRONG_TARGET_BONE_COUNT")
    meshes=[o for o in bpy.data.objects if o.type=="MESH" and
            any(m.type=="ARMATURE" and m.object==rig for m in o.modifiers)]
    need(bool(meshes),"NO_NATIVE_SKINNED_MATERIAL")
    for obj in bpy.data.objects:
        if obj.animation_data:obj.animation_data_clear()
    bmap={bf.canon(b.name):b.name for b in rig.pose.bones}
    rest=doc["bone_rest_map"]
    need(set(rest)==set(ORDER),"ORIGINAL_SOURCE_LOWERBODY_MISSING")
    mapping={k:bmap[bf.canon(rest[k]["node_name"])] for k in ORDER}
    need(len(set(mapping.values()))==9,"NATIVE_BONE_NAME_COLLISION")
    # Source: original real Three glTF source bind matrices, captured before warmup.
    SRC={k:mat(rest[k]["original_three_rest_world_matrix_column_major"]) for k in ORDER}
    # Target: actual ORIGINAL Blender GLB-rest world bone frames, no adapted pose.
    TGT={k:rig.matrix_world@rig.data.bones[mapping[k]].matrix_local for k in ORDER}
    X=[tuple(SRC[k].translation) for k in TRAIN]
    Y=[tuple(TGT[k].translation) for k in TRAIN]
    AF,scale,R=sim3(X,Y)
    ax=Matrix.Rotation(math.pi/2,4,"X")
    leg_source=(SRC["LeftHip"].translation-SRC["LeftKnee"].translation).length + \
               (SRC["LeftKnee"].translation-SRC["LeftAnkle"].translation).length
    leg_tgt=(TGT["LeftHip"].translation-TGT["LeftKnee"].translation).length + \
            (TGT["LeftKnee"].translation-TGT["LeftAnkle"].translation).length
    need(.3<leg_source<1.5 and .2<leg_tgt<2,"SOURCE_LEG_OR_WORLD_METRIC_INVALID")
    k=leg_tgt/leg_source
    rx=Matrix.Rotation(math.pi/2,3,"X")
    translate=TGT["Hips"].translation-k*rx@SRC["Hips"].translation
    AA=Matrix(((k*rx[0][0],k*rx[0][1],k*rx[0][2],translate.x),
               (k*rx[1][0],k*rx[1][1],k*rx[1][2],translate.y),
               (k*rx[2][0],k*rx[2][1],k*rx[2][2],translate.z),
               (0,0,0,1)))
    A_modes={"fixed_yup_to_zup_axis_only":AA,"five_landmark_rest_similarity":AF}
    fit={mode:{"train":points_rms(A,SRC,TGT,TRAIN),
               "heldout":points_rms(A,SRC,TGT,HOLD),
               "matrix_source_world_to_native_world_colmajor":mjson(A)}
         for mode,A in A_modes.items()}
    need(fit["five_landmark_rest_similarity"]["train"]["rms_m"]<
         fit["fixed_yup_to_zup_axis_only"]["train"]["rms_m"]+1e-5,
         "SIM3_TRAIN_FIT_LOST_TO_AXIS_CONTROL")
    frames=doc["frames"]
    invrest={key:SRC[key].inverted_safe() for key in ORDER}
    native_rest={key:TGT[key].copy() for key in ORDER}
    co=bf.foot_groups(meshes,rig,mapping)
    result=[]
    for mode,A in A_modes.items():
        for b in rig.pose.bones:
            b.rotation_mode="QUATERNION"
            b.rotation_quaternion=(1,0,0,0)
            b.location=(0,0,0)
        rig.matrix_world=rig.matrix_world.copy()
        bpy.context.view_layer.update()
        records={"L":[],"R":[]}
        err={key:[] for key in ("LeftAnkle","RightAnkle","LeftToe","RightToe")}
        source_target_displacements={key:[] for key in err}
        # This is the actual per-bone source world motion, including global target movement,
        # anchored to separately observed original source GLB-rest and target bind.
        for frame in frames:
            need(frame["i"]==len(records["L"]),"ACTUAL_FRAME_ORDER")
            now={key:mat(frame["pose_world_matrix_column_major"][key]) for key in ORDER}
            for key in ORDER:
                D=A@now[key]@invrest[key]@A.inverted_safe()
                desired=D@native_rest[key]
                rig.pose.bones[mapping[key]].matrix=rig.matrix_world.inverted_safe()@desired
                bpy.context.view_layer.update()
            for key in err:
                actual=rig.matrix_world@rig.pose.bones[mapping[key]].head
                source_expected=A@now[key].translation
                # Separate static source-rest morphology residual and timevarying driver.
                initial=A@SRC[key].translation
                target_base=native_rest[key].translation
                expect=target_base+(source_expected-initial)
                err[key].append((actual-expect).length)
            for side in ("L","R"):records[side].append(bf.observe(co[side]))
        trials={"mode":mode,"actual_native_blender_frames":360,
                "actual_native_skin_mesh_count":len(meshes),
                "source_controller_phases_are_not_true_contact":True,
                "real_native_foot_material":{side:compare(records[side],
                        [f["phases"][side] for f in frames]) for side in ("L","R")},
                "world_ankle_and_toe_delta_errors":{key:{
                    "p50_m":round(statistics.median(series),6),
                    "max_m":round(max(series),6)}
                    for key,series in err.items()},
                "physical_contact_accepted":False}
        result.append(trials)
    out={"schema":"scp.n03d-bg.world-similarity-source-to-native-360-v1",
         "source_class":"PUBLIC_ORIGINAL_CC0_THREE_CONTROLLER",
         "original_three_commit":bf.PIN,
         "source_pose_sha256":hashlib.sha256(Path(args.source).read_bytes()).hexdigest(),
         "source_model_git_blob":bf.FILES[args.rig][1],
         "source_model_sha256":hashlib.sha256(model).hexdigest(),
         "rig":args.rig,"blender_native_bones":len(rig.data.bones),
         "calibration_fitted_using_only_original_rest_bone_centres":list(TRAIN),
         "out_of_sample_calibration_joints":list(HOLD),
         "calibration_orthogonal_no_reflection":True,
         "calibration_rest_landmark_results":fit,
         "retarget_models":result,
         "source_and_native_same_public_GLBFIle":True,
         "measured_ground_force":False,"body_style_or_actor_identity_accepted":False,
         "true_sole_contact_accepted":False,"mvp_accepted":False,
         "status":"PASS_NARROW_SOURCE_TO_NATIVE_WORLD_MATCH_HOLD_PHYSICS"}
    need(out["measured_ground_force"] is False and out["mvp_accepted"] is False,
         "FALSE_SOURCE_GROUND_RELEASE")
    Path(args.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BG_ACTUAL_60HZ_SIM3_SOURCE_TO_NATIVE",json.dumps({
      "rig":args.rig,"fit":{k:{"train":v["train"],"heldout":v["heldout"]} for k,v in fit.items()},
      "trials":result,"status":out["status"]},sort_keys=True),flush=True)
if __name__=="__main__":main()
