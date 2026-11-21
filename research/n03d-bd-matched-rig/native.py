"""N03D-BD: real Blender thirdparty skinned model, SAME original 100STYLE motion for 3 rigs.

Two explicitly different rest-frame retarget projections, 360 real 60Hz evaluations.
Source ankle/toe and target foot material aren't anatomical equivalents.
Not an accepted full body locomotion or production retargeter.
"""
import argparse,hashlib,json,math,statistics,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector,Quaternion

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha,fk

SOURCE_BLOB="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61"
SOURCE_COMMIT="10938b4881b55c5801faded89e427407ddf14bce"
MODELS={
 "vsim":("76fb3eb2b23de748368b5fecc0862e06a0321e2c","game_engine"),
 "cc":("bdbdab04eb85903e46c56ff56c7a1ea0cbe9c78b","game_engine"),
 "rigify":("d3327b94c302278b5471c24d712ef5dc49f0d682","rigify"),
}
MAPS={
 "game_engine":{"Hips":"pelvis","LeftHip":"thigh_l","LeftKnee":"calf_l","LeftAnkle":"foot_l","LeftToe":"ball_l",
                "RightHip":"thigh_r","RightKnee":"calf_r","RightAnkle":"foot_r","RightToe":"ball_r"},
 "rigify":{"Hips":"spine","LeftHip":"thigh.L","LeftKnee":"shin.L","LeftAnkle":"foot.L","LeftToe":"toe.L",
           "RightHip":"thigh.R","RightKnee":"shin.R","RightAnkle":"foot.R","RightToe":"toe.R"}
}
def need(c,why):
    if not c:raise ValueError(why)
def sha(b):
    return hashlib.sha256(b).hexdigest()
def source_rotation(node,frame):
    result=Matrix.Identity(3)
    for key,v in zip(node["channels"],frame[node["start"]:node["start"]+len(node["channels"])]):
        if key.endswith("rotation"):
            result=result@Matrix.Rotation(math.radians(v),3,key[0])
    return result
def source_pos(node,frame):
    xyz=list(node["offset"])
    for key,v in zip(node["channels"],frame[node["start"]:node["start"]+len(node["channels"])]):
        if key.endswith("position"):xyz["XYZ".index(key[0])]+=v
    return Vector(xyz)
def get_source(bvh):
    d={n["name"]:n for n in bvh["nodes"] if not n["end"]}
    need(all(k in d for k in ["Hips","LeftHip","LeftKnee","LeftAnkle","LeftToe",
                              "RightHip","RightKnee","RightAnkle","RightToe"]),
         "REQUIRED_SOURCE_FOOT_HIERARCHY")
    return d
def cohorts(meshes,bones):
    """Fixed IDs weighted by named target foot/toe, not anatomical heel or measured sole."""
    out={"L":[],"R":[]}
    for m in meshes:
        groups={g.name:g.index for g in m.vertex_groups}
        for side,keys in (("L",("LeftAnkle","LeftToe")),("R",("RightAnkle","RightToe"))):
            relevant={groups[bones[k]] for k in keys if bones[k] in groups}
            if not relevant:continue
            scored=[]
            for v in m.data.vertices:
                mass=sum(g.weight for g in v.groups if g.group in relevant)
                if mass>=.40:scored.append(v.index)
            if scored:
                ev=m.evaluated_get(bpy.context.evaluated_depsgraph_get());geom=ev.to_mesh()
                try:
                    world=sorted([(float((ev.matrix_world@geom.vertices[i].co).z),i) for i in scored])
                finally:ev.to_mesh_clear()
                n=max(5,int(.25*len(world)))
                picks=[i for _,i in world[:n]]
                out[side].append({"obj":m,"ids":picks,
                                  "selected_weighted_vertices":len(scored),
                                  "bottom_rest_quartile_count":len(picks)})
    return out
def observe_cohort(blocks):
    points=[]
    for block in blocks:
        m=block["obj"];ob=m.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=ob.to_mesh()
        try:
            need(len(mesh.vertices)==len(m.data.vertices),"NATIVE_TOPOLOGY_CHANGED")
            for i in block["ids"]:
                v=ob.matrix_world@mesh.vertices[i].co
                need(all(math.isfinite(z) and abs(z)<100 for z in v),"NATIVE_MATERIAL_NONFINITE")
                points.append((float(v.x),float(v.y),float(v.z)))
        finally:ob.to_mesh_clear()
    need(len(points)>=5,"NO_FOOT_SKIN_COHORT")
    return {"x_m":sum(x for x,y,z in points)/len(points),
            "y_m":sum(y for x,y,z in points)/len(points),
            "min_z_m":min(z for x,y,z in points),
            "material_vertices":len(points)}
def diag(series,reference):
    vals=[r["min_z_m"] for r in series]
    speeds=[math.dist((series[i]["x_m"],series[i]["y_m"]),
                      (series[i-1]["x_m"],series[i-1]["y_m"]))*60 for i in range(1,len(series))]
    low=[speeds[i-1] for i in range(1,len(series)) if
         series[i]["min_z_m"]<=reference+.012 and series[i-1]["min_z_m"]<=reference+.012]
    return {"samples_60hz":len(series),"minimum_skin_z_m":round(min(vals),6),
            "maximum_skin_z_m":round(max(vals),6),
            "relative_min_reference_Z_m":round(reference,6),
            "candidate_near_low_adjacent_pairs":len(low),
            "p50_fullclip_stable_material_xy_speed_mps":round(statistics.median(speeds),6),
            "max_fullclip_stable_material_xy_speed_mps":round(max(speeds),6),
            "p50_near_low_stable_material_xy_speed_mps":round(statistics.median(low),6) if low else None,
            "source_ground_is_known":False,
            "true_force_contact_measured":False}
def sample_source(bvh):
    n0,n1=120,480
    heads={k:[] for k in ("LeftAnkle","RightAnkle","LeftToe","RightToe")}
    for i in range(n0,n1):
        p=fk(bvh,i)
        for k in heads:heads[k].append(p[k])
    scores={}
    for k,track in heads.items():
        floor=min(v[1] for v in track)
        slow=[math.dist((track[i][0],track[i][2]),(track[i-1][0],track[i-1][2]))*.01*60
               for i in range(1,len(track))
               if track[i][1]<floor+1.5 and track[i-1][1]<floor+1.5]
        scores[k]={"source_low_velocities_count":len(slow),
                   "source_p50_low_velocity_mps":round(statistics.median(slow),6) if slow else None,
                   "source_low_Y_cm":round(floor,6),
                   "source_force_contact_verified":False}
    return scores
def main():
    parser=argparse.ArgumentParser()
    for key in ("model","candidate","motion","out"):parser.add_argument("--"+key,required=True)
    a=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    need(a.candidate in MODELS,"CANDIDATE_UNKNOWN")
    mb=Path(a.model).read_bytes();data=Path(a.motion).read_bytes()
    need(git_blob_sha(mb)==MODELS[a.candidate][0],"MODEL_CONTENT_OR_RIGHTS_CHANGED")
    need(Path(a.motion).name=="Neutral_FW.bvh" and git_blob_sha(data)==SOURCE_BLOB,
         "SOURCE_MOTION_CONTENT_CHANGED")
    bvh=parse_bvh(data)
    need(bvh["count"]==2400 and abs(bvh["frame_time"]-1/60)<1e-5,"SOURCE_CLOCK")
    nodes=get_source(bvh)
    # Four sources share exact same real frame window 120..479, no re-selected gain.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(a.model).resolve()))
    rigs=[x for x in bpy.data.objects if x.type=="ARMATURE"]
    need(len(rigs)==1,"TARGET_RIG_COUNT")
    rig=rigs[0]
    skinned=[x for x in bpy.data.objects if x.type=="MESH" and
             any(m.type=="ARMATURE" and m.object==rig for m in x.modifiers)]
    need(len(skinned)>=1,"NO_ACTUAL_TARGET_SKIN")
    # Source model may have unrelated original action. This is a NEW matched-source ablation.
    for x in bpy.data.objects:
        if x.animation_data:x.animation_data_clear()
    mapping=MAPS[MODELS[a.candidate][1]]
    need(all(t in rig.pose.bones for t in mapping.values()),"TARGET_MISSING_CANONICAL_LOWER_BONES")
    rig_matrix=rig.matrix_world.copy()
    conv=Matrix.Rotation(math.pi/2,3,"X")
    src_len=(Vector(nodes["LeftKnee"]["offset"]).length+
             Vector(nodes["LeftAnkle"]["offset"]).length)*.01
    target_len=rig.data.bones[mapping["LeftHip"]].length+rig.data.bones[mapping["LeftKnee"]].length
    need(src_len>.2 and target_len>.2 and target_len<2.5,"LEG_METRIC_SANITY")
    length_ratio=target_len/src_len
    # m source root motion delta already centimeters; adapted to target leg length.
    start_frame=bvh["frames"][120]
    root0=source_pos(nodes["Hips"],start_frame)
    path=Path(a.out);trials=[]
    rig.data.pose_position="POSE"
    for mode in ("direct_canonical","rest_frame_conjugated"):
        # Reset completely to original rest; these are intentionally diagnostic, not production skin.
        for bone in rig.pose.bones:
            bone.rotation_mode="QUATERNION"
            bone.rotation_quaternion=Quaternion((1,0,0,0))
            bone.location=(0,0,0)
        rig.matrix_world=rig_matrix.copy()
        bpy.context.view_layer.update()
        groups=cohorts(skinned,mapping)
        pairs={k:len(groups[s]) for s,k in (("L","L"),("R","R"))}
        need(all(len(groups[s])>=1 for s in ("L","R")),"MISSING_WEIGHTED_FOOT_COHORT")
        stream={"L":[],"R":[]}
        for k in range(360):
            frame=bvh["frames"][120+k]
            for src_name,tgt_name in mapping.items():
                src_rot=conv@source_rotation(nodes[src_name],frame)@conv.inverted()
                bone=rig.pose.bones[tgt_name]
                if mode=="rest_frame_conjugated":
                    rb=rig.data.bones[tgt_name]
                    rest=rb.matrix_local.to_3x3()
                    if rb.parent:
                        rest=rb.parent.matrix_local.to_3x3().inverted()@rest
                    src_rot=rest.inverted()@src_rot@rest
                bone.rotation_quaternion=src_rot.to_quaternion()
            moved=conv@(source_pos(nodes["Hips"],frame)-root0)
            moved*=.01*length_ratio
            rig.matrix_world=Matrix.Translation(moved)@rig_matrix
            bpy.context.view_layer.update()
            for side in ("L","R"):
                stream[side].append(observe_cohort(groups[side]))
        ref=min(v["min_z_m"] for s in stream.values() for v in s)
        trial={"mode":mode,"source_frames":[120,479],"source_fps":60,
               "native_actually_evaluated_skinned_60hz_samples_per_foot":360,
               "actual_skin_cohorts":{side:sum(t["bottom_rest_quartile_count"] for t in groups[side])
                                      for side in ("L","R")},
               "source_floor_calibrated":False,
               "applied_target_root_scale_ratio":round(length_ratio,6),
               "output_reference_is_own_lowest_skin_sample":True,
               "rig_foot_measures":{s:diag(track,ref) for s,track in stream.items()}}
        trials.append(trial)
    out={"schema":"scp.n03d-bd.same-100style-rig-matched-native.v1",
         "candidate":a.candidate,"target_native_rig_bones":len(rig.data.bones),
         "source_class":"PUBLIC_SOURCE_RIGHTS_RESEARCH_ONLY",
         "model_github_blob":MODELS[a.candidate][0],
         "model_sha256":sha(mb),"original_100style_blob":SOURCE_BLOB,
         "source_sha256":sha(data),"source_commit":SOURCE_COMMIT,
         "source_mocap_ground_force_proven":False,"source_rights_paid_or_protected":False,
         "true_anatomical_correspondence_accepted":False,
         "source_same_360_frames_for_all_candidates":True,
         "source_slow_ankle_toe_diagnostics":sample_source(bvh),
         "original_motion_file_published":False,
         "actual_blender_skin_actuated":True,
         "physical_gait_accepted":False,"mvp_accepted":False,
         "status":"PASS_NARROW_COMMON_SOURCE_NATIVE_GEOMETRY_HOLD_GAIT",
         "trials":trials}
    need(len(trials)==2 and all(v["native_actually_evaluated_skinned_60hz_samples_per_foot"]==360
                                 for v in trials),"INSUFFICIENT_NATIVE_CLOCK")
    path.write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BD_ACTUAL_COMMON_100STYLE_NATIVE_TWO_RETARGETS",json.dumps({
      "candidate":a.candidate,"bones":out["target_native_rig_bones"],
      "source_sha256":out["source_sha256"],
      "modes":[{"mode":v["mode"],"foot":v["rig_foot_measures"],
                 "cohort":v["actual_skin_cohorts"]} for v in trials],
      "status":out["status"]},sort_keys=True),flush=True)
if __name__=="__main__":main()
