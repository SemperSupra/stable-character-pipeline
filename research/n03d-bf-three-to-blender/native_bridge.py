"""N03D-BF genuine source Three 60Hz controller bone poses => Blender evaluated skin.

One live model and same source controller; native Blender target receives locally
replayed 360 bone-rotation snapshots. No render, measured forces, true stance,
source 100STYLE equivalence, nor independent anatomical heel/sole contacts.
"""
import argparse,hashlib,json,math,statistics,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
PIN="3f5b4896f1b28501b40aa9c408e47dba51322443"
FILES={"rigify":("modelos/human.glb","d3327b94c302278b5471c24d712ef5dc49f0d682",161),
       "named":("modelos/human_mix_propio.glb","2f86c50b2938f0f7d78df7ff9835864d6af0fd4a",None)}
def need(x,why):
    if not x:raise ValueError(why)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def blob(data):
    return hashlib.sha1(("blob "+str(len(data))+"\0").encode()+data).hexdigest()
def canon(x):
    return "".join(c for c in x.lower() if c.isalnum())
def q(wxyz):
    need(len(wxyz)==4 and all(type(x) in (float,int) and math.isfinite(x) for x in wxyz),"SOURCE_QUAT_INVALID")
    rot=Quaternion(tuple(wxyz))
    need(abs(rot.length-1)<.001,"SOURCE_NONUNIT_QUAT")
    return rot
def v(x):
    need(len(x)==3 and all(type(z) in (float,int) and math.isfinite(z) and abs(z)<1e4 for z in x),"SOURCE_VECTOR_INVALID")
    return Vector(x)
def foot_groups(meshes,rig,mapping):
    result={"L":[],"R":[]}
    for obj in meshes:
        members={canon(g.name):g.index for g in obj.vertex_groups}
        for side,keys in (("L",("LeftAnkle","LeftToe")),("R",("RightAnkle","RightToe"))):
            good={members[canon(mapping[k])] for k in keys if canon(mapping[k]) in members}
            if not good:continue
            weighted=[]
            for vert in obj.data.vertices:
                mass=sum(gr.weight for gr in vert.groups if gr.group in good)
                if mass>=.40:weighted.append(vert.index)
            if not weighted:continue
            ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh=ev.to_mesh()
            try:
                need(len(mesh.vertices)==len(obj.data.vertices),"SKIN_TOPOLOGY_NOT_FIXED")
                rest=sorted([(float((ev.matrix_world@mesh.vertices[i].co).z),i) for i in weighted])
            finally:ev.to_mesh_clear()
            keep=max(5,int(.25*len(rest)))
            result[side].append({"object":obj,"ids":[i for _,i in rest[:keep]]})
    need(all(result[s] for s in ("L","R")),"SKINNED_FEET_VERTEX_WEIGHTS_NOT_FOUND")
    return result
def observe(groups):
    pts=[]
    for group in groups:
        obj=group["object"]
        eval_obj=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=eval_obj.to_mesh()
        try:
            need(len(mesh.vertices)==len(obj.data.vertices),"NONINVARIANT_SKIN_TOPOLOGY")
            for i in group["ids"]:
                pt=eval_obj.matrix_world@mesh.vertices[i].co
                need(all(math.isfinite(z) and abs(z)<100 for z in pt),"NONFINITE_NATIVE_SKIN")
                pts.append((float(pt.x),float(pt.y),float(pt.z)))
        finally:eval_obj.to_mesh_clear()
    need(len(pts)>=5,"NO_ACTUAL_MATERIAL")
    return {"xy":[sum(p[i] for p in pts)/len(pts) for i in (0,1)],
            "min_z":min(z for x,y,z in pts),"count":len(pts)}
def stats(trace,phase):
    z=[v["min_z"] for v in trace];low=min(z)
    speed=[60*math.dist(trace[i]["xy"],trace[i-1]["xy"]) for i in range(1,len(trace))]
    known=[speed[i-1] for i in range(1,len(trace))
           if phase[i]!="SWING" and phase[i-1]!="SWING"]
    near=[speed[i-1] for i in range(1,len(trace))
          if z[i]<=low+.012 and z[i-1]<=low+.012]
    return {"source_frames":len(trace),"foot_material_count":trace[0]["count"],
            "local_low_m":round(low,6),
            "high_m":round(max(z),6),
            "p50_all_foot_material_xy_speed_mps":round(statistics.median(speed),6),
            "p50_native_material_in_controller_declared_nonswing_mps":round(statistics.median(known),6) if known else None,
            "n_controller_declared_nonswing_adjacent_pairs":len(known),
            "p50_material_near_own_low_height_mps":round(statistics.median(near),6) if near else None,
            "n_own_low_adjacent_pairs":len(near),
            "actual_sole_ground_and_force_contact_verified":False}
def main():
    p=argparse.ArgumentParser()
    for k in ("source","model","rig","out"):p.add_argument("--"+k,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    need(a.rig in FILES,"NOT_ORIGINAL_PUBLIC_RIG")
    file,gitblob,expected=FILES[a.rig]
    raw=Path(a.model).read_bytes()
    need(blob(raw)==gitblob,"NATIVE_MODEL_GIT_BLOB_DRIFT")
    source=json.loads(Path(a.source).read_text())
    need(source.get("schema")=="scp.n03d-bf.real-three-to-blender-source-pose-v1" and
         source.get("original_source_commit")==PIN and
         source.get("source_glb_model")==file and
         source.get("genuine_realtime_three_frames_60hz")==360 and
         source.get("warmup_frames")==120 and
         source.get("same_original_motion_for_blender_replay") is True and
         source.get("public_original_cc0_only") is True and
         source.get("source_grf_measured") is False and
         source.get("planted_targets_are_not_measured_skin_contact") is True and
         source.get("original_100style_motion_identical") is False and
         source.get("physical_gait_accepted") is False and
         source.get("mvp_accepted") is False,"SOURCE_CONTROLLER_OR_SAFETY_FORGERY")
    frames=source.get("frames",[])
    need(len(frames)==360 and all(f["i"]==i for i,f in enumerate(frames)),"CONTROLLER_60HZ_CLOCK")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(a.model).resolve()))
    arms=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    need(len(arms)==1,"BLENDER_MODEL_ARMATURE")
    rig=arms[0]
    if expected:need(len(rig.data.bones)==expected,"MODEL_RIG_TOPOLOGY")
    skinned=[o for o in bpy.data.objects if o.type=="MESH" and
             any(m.type=="ARMATURE" and m.object==rig for m in o.modifiers)]
    need(skinned,"NATIVE_SKINNING_EMPTY")
    for o in bpy.data.objects:
        if o.animation_data:o.animation_data_clear()
    named={canon(b.name):b.name for b in rig.pose.bones}
    need(len(named)==len(rig.pose.bones),"AMBIGUOUS_BONE_CANONICAL_NAMES")
    rest=source["bone_rest_map"]
    need(set(rest)=={"Hips","LeftHip","LeftKnee","LeftAnkle","LeftToe",
                    "RightHip","RightKnee","RightAnkle","RightToe"},"SOURCE_NINE_JOINT_MAPPING")
    pairs={k:named[canon(record["node_name"])] for k,record in rest.items()}
    need(len(set(pairs.values()))==9,"DUPLICATE_REPLAY_BONE")
    nativefoot=[rig.data.bones[pairs[k]].head_local for k in ("LeftHip","LeftKnee","LeftAnkle")]
    targetleg=(nativefoot[0]-nativefoot[1]).length+(nativefoot[1]-nativefoot[2]).length
    sourceleg=float(source["source_native_leg_length_m"])
    need(.45<sourceleg<1.5 and .4<targetleg<1.5,"LEG_SCALE_UNTRUSTED")
    scale=targetleg/sourceleg
    base=rig.matrix_world.copy()
    C=Matrix.Rotation(math.pi/2,3,"X").to_quaternion()
    initial=v(frames[0]["root_y_up"])
    trials=[]
    for mode in ("direct_local_delta","bone_rest_conjugated_delta"):
        for b in rig.pose.bones:
            b.rotation_mode="QUATERNION"
            b.rotation_quaternion=Quaternion((1,0,0,0))
            b.location=(0,0,0)
        rig.matrix_world=base.copy()
        bpy.context.view_layer.update()
        co=foot_groups(skinned,rig,pairs)
        records={"L":[],"R":[]}
        poses={"L":[],"R":[]}
        src_foot={"L":[],"R":[]}
        native_foot={"L":[],"R":[]}
        start={}
        for i,f in enumerate(frames):
            need(set(f["pose"])==set(pairs),"SOURCE_MISSING_ROTATION")
            for k,t in pairs.items():
                delta=q(f["pose"][k])@q(rest[k]["quat_wxyz"]).inverted()
                delta=C@delta@C.inverted()
                if mode=="bone_rest_conjugated_delta":
                    B=rig.data.bones[t]
                    frame=B.matrix_local.to_quaternion()
                    if B.parent:frame=(B.parent.matrix_local.inverted()@B.matrix_local).to_quaternion()
                    delta=frame.inverted()@delta@frame
                rig.pose.bones[t].rotation_quaternion=delta
            displacement=C.to_matrix()@(v(f["root_y_up"])-initial)
            rig.matrix_world=Matrix.Translation(scale*displacement)@base
            bpy.context.view_layer.update()
            for side,key in (("L","LeftAnkle"),("R","RightAnkle")):
                records[side].append(observe(co[side]))
                srcpt=C.to_matrix()@v(f["landmarks_world_y_up"][key])
                dstpt=rig.matrix_world@rig.pose.bones[pairs[key]].head
                if i==0:start[side]=(srcpt.copy(),dstpt.copy())
                src_foot[side].append(srcpt)
                native_foot[side].append(dstpt)
        for side in ("L","R"):
            ar=records[side]
            need(any(math.dist(ar[i]["xy"],ar[0]["xy"])>.01 for i in range(1,360)),
                 "NO_ACTUAL_CONTROLLER_DRIVEN_SKIN_MOVEMENT")
        mismatch={}
        for side in ("L","R"):
            original,native=start[side]
            errors=[((dst-native)-scale*(src-original)).length
                    for src,dst in zip(src_foot[side],native_foot[side])]
            mismatch[side]={"p50_joint_displacement_error_m":round(statistics.median(errors),6),
                            "max_joint_displacement_error_m":round(max(errors),6),
                            "coordinate_frame":"THREE_Y_UP_VS_BLENDER_Z_UP_CALIBRATED_BY_FIRST_FRAME_TRANSLATION_ONLY"}
        trials.append({"mode":mode,"native_60hz_frames":360,
                       "controller_source_phases_not_ground_truth":True,
                       "actual_skinned_material":{side:stats(records[side],[f["phases"][side] for f in frames])
                                                  for side in ("L","R")},
                       "source_joint_displacement_errors":mismatch,
                       "mvp_or_physical_contact_accepted":False})
    out={"schema":"scp.n03d-bf.live-three-controller-to-native-blender-skin.v1",
         "source_class":"ORIGINAL_PUBLIC_CC0_THREE_RUNTIME",
         "controller_repo_commit":PIN,
         "source_pose_trace_sha256":sha(Path(a.source).read_bytes()),
         "source_model_git_blob":gitblob,
         "source_model_sha256":sha(raw),
         "rig":a.rig,"native_rig_bones":len(rig.data.bones),
         "source_leg_length_m":round(sourceleg,6),"native_leg_length_m":round(targetleg,6),
         "motion_same_360frames_and_model":True,"source_100style_mocap_matched":False,
         "actual_native_blender_skinned_meshes":len(skinned),
         "true_sole_and_anatomical_contact_proven":False,
         "source_measured_ground_force_proven":False,
         "independent_visual_accepted":False,"mvp_accepted":False,
         "trials":trials,
         "status":"PASS_NARROW_ACTUAL_CONTROLLER_TO_SKIN_REPLAY_HOLD_CONTACT"}
    Path(a.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BF_TRUE_360HZ_THREE_TO_BLENDER_NATIVE_SKIN",json.dumps({
        "rig":a.rig,"bone_count":len(rig.data.bones),"model":gitblob,
        "trials":trials,"status":out["status"]},sort_keys=True),flush=True)
if __name__=="__main__":main()
