"""N03D-BJ: 100STYLE BVH true FK → same Aster/Juniper MPFB153/53,
real 360x60Hz anatomically named joint traces and independent 5/4 Procrustes.

Original source first frame is WALK, not a neutral rest. Fitted calibration
therefore cannot be reinterpreted as true rest T-pose or anatomical equivalence.
Existing BE native direct and rest-basis adapters unchanged; compare their
time-varying world joint paths vs source for the same source time and body.
"""
import argparse,hashlib,json,math,statistics,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector,Quaternion
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"n03d-be-morph-controlled"))
sys.path.insert(0,str(HERE.parent/"n03d-bd-matched-rig"))
sys.path.insert(0,str(HERE.parent/"r078-r009-mpfb-pair"))
sys.path.insert(0,str(HERE.parent/"r088-motion-real"))
import morph_matched as be
import native as bd
import contract
from bvh_preflight import parse_bvh,git_blob_sha,fk
SOURCE="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61"
TRAIN=("Hips","LeftHip","RightHip","LeftKnee","RightKnee")
HELDOUT=("LeftAnkle","RightAnkle","LeftToe","RightToe")
ALL=TRAIN+HELDOUT
MORPH={"AsterOriginal":"9156e167a19083500fc5323155166abd3daa2a93510bacb8beeb7de8c83c4a4b",
       "JuniperOriginal":"8dfa35c38f3df7cbff4601232d4a8b7dcc1d0ee74f34ead424c787cf638aa918"}
def need(x,msg):
    if not x:raise ValueError(msg)
def sim3(xs,ys):
    x=np.array(xs,dtype=float);y=np.array(ys,dtype=float)
    need(x.shape==(5,3) and y.shape==(5,3) and
         np.isfinite(x).all() and np.isfinite(y).all(),"SOURCE_REST_5TRAIN_INVALID")
    xc=x-x.mean(0);yc=y-y.mean(0)
    v=np.linalg.svd(xc,compute_uv=False)
    need(v[1]>1e-5,"SOURCE_REST_COLLINEAR_LEGS")
    u,s,vt=np.linalg.svd(xc.T@yc)
    R=vt.T@np.diag([1.,1.,np.linalg.det(vt.T@u.T)])@u.T
    scale=float((yc*(xc@R.T)).sum()/(xc*xc).sum())
    need(.3<scale<3 and np.linalg.det(R)>.9999,"REFLECTED_OR_UNPHYSICAL_SCALE")
    t=y.mean(0)-scale*R@x.mean(0)
    return scale,R,t
def pct(x,k):
    s=sorted(x)
    return round(float(s[min(len(s)-1,int(math.ceil(k*len(s)))-1)]),6)
def diagnostics(positions):
    traces={}
    for n,series in positions.items():
        need(len(series)==360,"SOURCE_TRACE_INCOMPLETE")
        dist=[(series[i]-series[i-1]).length*60 for i in range(1,360)]
        traces[n]={"speed_p50_mps":pct(dist,.5),"speed_p95_mps":pct(dist,.95),
                   "total_displacement_m":round((series[-1]-series[0]).length,6)}
    return traces
def source_world(bvh):
    d={}
    for i in range(120,480):
        native=fk(bvh,i)
        need(all(k in native for k in ALL),"MOCAP_NINE_FK_JOINT_MISSING")
        for name in ALL:
            # Imported actual CMU/100STYLE source BVH world coordinates Y-up in cm.
            d.setdefault(name,[]).append(Vector(native[name])*.01)
    need(len(d)==9 and all(len(v)==360 for v in d.values()),
         "SOURCE_NATIVE_FK_WINDOW_360")
    return d
def actor(whose,bvh,src):
    hs,ts,props=be.setup()
    profile=next(x for x in contract.PROFILES if x["name"]==whose)
    rig_results=[]
    for kind in ("default","game_engine"):
        body,arm,raw,shape,macros,ignored,after,drift=be.create(hs,ts,props,profile,kind)
        need(shape["sha256"]==MORPH[whose],"ORIGINAL_EVALUATED_SHAPE_SOURCE_DRIFT")
        mapping=be.RIGS[kind]
        arm.data.pose_position="REST"
        bpy.context.view_layer.update()
        target_start={k:arm.matrix_world@arm.data.bones[mapping[k]].head_local
                      for k in ALL}
        s,R,t=sim3([tuple(src[n][0]) for n in TRAIN],
                   [tuple(target_start[n]) for n in TRAIN])
        def trans(q):
            v=s*R@np.array(q,float)+t
            return Vector(tuple(float(x) for x in v))
        static={k:round((trans(src[k][0])-target_start[k]).length,6) for k in ALL}
        rootStart=target_start["Hips"]
        scale=s
        need(max(static[k] for k in TRAIN)<.3,"MORPH_AND_SOURCE_REST_TRAIN_UNMATCHABLE")
        for m in body.modifiers:
            if m.type!="ARMATURE":m.show_viewport=False
        arm.data.pose_position="POSE"
        base=arm.matrix_world.copy()
        native_rest={k:arm.data.bones[mapping[k]].matrix_local.copy() for k in ALL}
        source_nodes=bd.get_source(bvh)
        conv=Matrix.Rotation(math.pi/2,3,"X")
        source_len=(Vector(source_nodes["LeftKnee"]["offset"]).length+
                    Vector(source_nodes["LeftAnkle"]["offset"]).length)*.01
        target_leg=(target_start["LeftHip"]-target_start["LeftKnee"]).length + \
                   (target_start["LeftKnee"]-target_start["LeftAnkle"]).length
        need(.4<target_leg<1.4 and .4<source_len<1.4,"SOURCE_TARGET_LEG_METRIC_INVALID")
        root0=bd.source_pos(source_nodes["Hips"],bvh["frames"][120])
        trials=[]
        for mode in ("direct_canonical","rest_frame_conjugated"):
            arm.data.pose_position="POSE"
            for b in arm.pose.bones:
                b.rotation_mode="QUATERNION"
                b.rotation_quaternion=Quaternion((1,0,0,0))
                b.location=(0,0,0)
            arm.matrix_world=base.copy()
            target={k:[] for k in ALL}
            checks=[]
            for i in range(360):
                f=bvh["frames"][120+i]
                for n,tgt in mapping.items():
                    rot=conv@bd.source_rotation(source_nodes[n],f)@conv.inverted()
                    if mode=="rest_frame_conjugated":
                        b=arm.data.bones[tgt]
                        rr=b.matrix_local.to_3x3()
                        if b.parent:rr=b.parent.matrix_local.to_3x3().inverted()@rr
                        rot=rr.inverted()@rot@rr
                    arm.pose.bones[tgt].rotation_quaternion=rot.to_quaternion()
                shift=conv@(bd.source_pos(source_nodes["Hips"],f)-root0)
                shift*=.01*target_leg/source_len
                arm.matrix_world=Matrix.Translation(shift)@base
                bpy.context.view_layer.update()
                for k in ALL:
                    target[k].append(arm.matrix_world@arm.pose.bones[mapping[k]].head)
                if i in (0,80,160,240,359):
                    checks.append(be.native_local_skin_digest(body))
            need(len(set(checks))>=3,"UNDEFORMED_REST_ONLY_FALSE_NATIVE")
            errs={}
            for k in ALL:
                # Time-varying source delta test is independent of static
                # rest mismatch; the target first actual pose is its own origin.
                actual=target[k]
                original=src[k]
                want=[trans(orig)-trans(original[0]) for orig in original]
                errors=[((dst-actual[0])-wanted).length
                        for dst,wanted in zip(actual,want)]
                need(len(errors)==360 and all(math.isfinite(x) for x in errors),
                     "NONFINITE_SOURCE_TO_TARGET_WORLD_RESIDUAL")
                errs[k]={"p50_dynamic_displacement_error_m":pct(errors,.5),
                         "p95_dynamic_displacement_error_m":pct(errors,.95),
                         "max_dynamic_displacement_error_m":round(max(errors),6),
                         "target_world_step_speed_p50_mps":diagnostics({k:actual})[k]["speed_p50_mps"]}
            trials.append({"rig":kind,"mode":mode,"actual_native_60hz_frames":360,
                           "source_fk_motion_world_samples":360,
                           "native_real_body_local_shape_sha_samples":checks,
                           "actual_deformed_skin_verified":True,
                           "source_fk_to_native_dynamic_residuals":errs,
                           "true_ground_or_force_proven":False,
                           "mvp_accepted":False})
        rig_results.append({"rig":kind,"bone_count":len(arm.data.bones),
                            "actual_same_source_evaluated_shape_sha256":shape["sha256"],
                            "actual_native_source_pre_rig_shape_vertices":shape["vertices"],
                            "first_recorded_walk_pose_used_not_source_tpose":True,
                            "source_mocap_vs_target_rest_calibration_fit_scale":round(s,8),
                            "five_training_joints":list(TRAIN),
                            "four_heldout_joints":list(HELDOUT),
                            "source_to_native_walkfirst_rest_alignment_errors_m":static,
                            "modes":trials})
    need(len(rig_results)==2 and
         rig_results[0]["actual_same_source_evaluated_shape_sha256"]==
         rig_results[1]["actual_same_source_evaluated_shape_sha256"],
         "NOT_IDENTICAL_ACTOR_MORPHOLOGY_RIGS")
    return rig_results
def main():
    ap=argparse.ArgumentParser()
    for key in ("actor","motion","out"):ap.add_argument("--"+key,required=True)
    a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
    need(a.actor in MORPH,"PROTECTED_OR_UNKNOWN_MODEL_NOT_ALLOWED")
    blob=Path(a.motion).read_bytes()
    need(git_blob_sha(blob)==SOURCE,"SOURCE_100STYLE_ORIGIN_NOT_PINNED")
    bvh=parse_bvh(blob)
    need(bvh["count"]==2400 and abs(bvh["frame_time"]-1/60)<1e-5,
         "SOURCE_100STYLE_60HZ_CLOCK")
    source=source_world(bvh)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rigs=actor(a.actor,bvh,source)
    out={"schema":"scp.n03d-bj.same-morph-source-fk-to-blender-world-joints.v1",
         "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
         "actor":a.actor,"original_100style_source_git_blob":SOURCE,
         "original_100style_source_sha256":hashlib.sha256(blob).hexdigest(),
         "source_100style_frame_window":[120,479],"true_source_100style_clock_hz":60,
         "official_mpfb_source_commit":contract.UPSTREAM,
         "source_world_fk":diagnostics({k:source[k] for k in ALL}),
         "source_no_ground_reaction_force_available":True,
         "source_first_frame_is_walk_not_neutral_rest":True,
         "fitted_holdout_used_in_training":False,
         "true_anatomical_side_or_sole_accepted":False,
         "photo_or_identity_protected_used":False,"mvp_accepted":False,
         "rigs":rigs,
         "status":"PASS_NARROW_MORPH_MATCHED_60HZ_SOURCE_NATIVE_TRAJECTORY_HOLD_GAIT"}
    Path(a.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BJ_SOURCE_FK_ACTUAL_NATIVE_60HZ_RESIDUAL",json.dumps({
        "actor":a.actor,
        "source":out["source_world_fk"],
        "models":[{"rig":v["rig"],"fit":v["source_to_native_walkfirst_rest_alignment_errors_m"],
                  "modes":[{"mode":t["mode"],"resid":t["source_fk_to_native_dynamic_residuals"]}
                           for t in v["modes"]]} for v in rigs],
        "status":out["status"]},sort_keys=True))
if __name__=="__main__":main()
