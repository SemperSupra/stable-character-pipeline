"""N03D-BE: native official MPFB exact matched Aster/Juniper morphology rig 163 vs 53.

This uses the SAME original model generation API + macro sliders and same
recorded 100STYLE source frames, source-root deltas and bone projection on
both rig types. An actual weighted body-foot surface is measured, NOT a shoe.
No ground truth, ROM, foot anatomy, physical gait, appearance, film or R009 pass.
"""
import argparse,hashlib,importlib,json,math,statistics,struct,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector,Quaternion

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE.parent/"r078-r009-mpfb-pair"))
import contract as c
sys.path.insert(0,str(HERE.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha
sys.path.insert(0,str(HERE.parent/"n03d-bd-matched-rig"))
from native import source_rotation,source_pos

BVH_SHA1="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61"
RIGS=("default","game_engine")
NAMES=("AsterOriginal","JuniperOriginal")
MODES=("direct_canonical","rest_frame_conjugated")
MAP={
"default":{"Hips":"pelvis","LeftHip":"upperleg01.L","LeftKnee":"lowerleg01.L",
           "LeftAnkle":"foot.L","RightHip":"upperleg01.R",
           "RightKnee":"lowerleg01.R","RightAnkle":"foot.R"},
"game_engine":{"Hips":"pelvis","LeftHip":"thigh_l","LeftKnee":"calf_l",
               "LeftAnkle":"foot_l","LeftToe":"ball_l",
               "RightHip":"thigh_r","RightKnee":"calf_r",
               "RightAnkle":"foot_r","RightToe":"ball_r"}
}
def need(ok,msg):
    if not ok:raise ValueError(msg)
def digest(b):
    return hashlib.sha256(b).hexdigest()
def services():
    import addon_utils
    mod="bl_ext.user_default.mpfb"
    if not addon_utils.check(mod)[1]:
        addon_utils.enable(mod,default_set=False,persistent=False)
    need(addon_utils.check(mod)[1],"OFFICIAL_MPF_EXTENSION_NOT_FOUND")
    H=importlib.import_module(mod+".services.humanservice").HumanService
    T=importlib.import_module(mod+".services.targetservice").TargetService
    P=importlib.import_module(mod+".entities.objectproperties").HumanObjectProperties
    return H,T,P
def verts(body):
    return [tuple(float(z) for z in v.co) for v in body.data.vertices]
def shape_diff(a,b):
    need(len(a)==len(b) and len(a)>10000,"MORPHOLOGY_VERTEX_COUNT_DIFFERENT")
    delta=[math.dist(x,y) for x,y in zip(a,b)]
    return {"count":len(a),"max_rest_vertex_deviation_m":round(max(delta),9),
            "p50_rest_vertex_deviation_m":round(statistics.median(delta),9),
            "same_morphology_max_1mm":max(delta)<=.001}
def observed_weighted(body,rig,bone_name,cache):
    index=body.vertex_groups.get(bone_name)
    need(index is not None,"NO_ACTUAL_FOOT_SKIN_WEIGHTS_"+bone_name)
    valid=[v.index for v in body.data.vertices
           if sum(g.weight for g in v.groups if g.group==index.index)>=.35]
    need(len(valid)>=10,"INSUFFICIENT_FOOT_WEIGHT_VERTICES_"+bone_name)
    b=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=b.to_mesh()
    try:
        need(len(mesh.vertices)==len(body.data.vertices),"EVALUATED_TOPOLOGY")
        bottom=sorted(valid,key=lambda i:(b.matrix_world@mesh.vertices[i].co).z)
        indices=bottom[:max(5,len(bottom)//5)]
    finally:b.to_mesh_clear()
    cache[bone_name]=indices
    return {"skin_weighted_vertices":len(valid),
            "bottom_fifth_source_foot_vertices":len(indices)}
def observe(body,ids):
    obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=obj.to_mesh()
    try:
        points=[obj.matrix_world@mesh.vertices[i].co for i in ids]
    finally:obj.to_mesh_clear()
    return (sum(p.x for p in points)/len(points),
            sum(p.y for p in points)/len(points),
            min(p.z for p in points))
def summary(series):
    speeds=[math.hypot(series[i][0]-series[i-1][0],series[i][1]-series[i-1][1])*60
            for i in range(1,len(series))]
    low=min(x[2] for x in series)
    selected=[speeds[i-1] for i in range(1,len(series))
              if series[i][2]<=low+.012 and series[i-1][2]<=low+.012]
    return {"frames":len(series),"min_native_foot_body_z_m":round(low,6),
            "max_native_foot_body_z_m":round(max(x[2] for x in series),6),
            "p50_fullclip_stable_body_foot_xy_speed_mps":round(statistics.median(speeds),6),
            "max_fullclip_stable_body_foot_xy_speed_mps":round(max(speeds),6),
            "candidate_low_relative_pairs":len(selected),
            "p50_low_relative_body_foot_xy_speed_mps":round(statistics.median(selected),6) if selected else None,
            "floor_calibrated":False,"ground_force_measured":False,"real_shoe_mesh_measured":False}
def build_pair(hs,ts,props):
    originals=[]
    for profile in c.PROFILES:
        variants={}
        for rig_name in RIGS:
            body=hs.create_human()
            need(body and body.type=="MESH","HUMAN_MESH_CREATION")
            rig=hs.add_builtin_rig(body,rig_name,import_weights=True)
            need(rig and rig.type=="ARMATURE","ACTUAL_RIG_CREATION")
            for key in c.PHENOTYPE_KEYS:
                props.set_value(key,profile[key],entity_reference=body)
            ts.reapply_macro_details(body)
            hs.refit(body)
            body.name=f"{profile['name']}_{rig_name}_Body"
            rig.name=f"{profile['name']}_{rig_name}_Rig"
            need(any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers),"MISSING_REAL_SKIN")
            bpy.context.view_layer.update()
            variants[rig_name]={"body":body,"rig":rig,"rest":verts(body),
                                "count":len(rig.data.bones)}
        diffs=shape_diff(variants["default"]["rest"],variants["game_engine"]["rest"])
        originals.append({"actor":profile["name"],"profile":{k:profile[k] for k in c.PHENOTYPE_KEYS},
                          "versions":variants,"shape":diffs})
    return originals
def actuate(actor,bvh,mapped_nodes):
    trials=[]
    for rig_name,variant in actor["versions"].items():
        rig=variant["rig"];body=variant["body"]
        mapping=MAP[rig_name]
        missing=[(s,t) for s,t in mapping.items() if t not in rig.pose.bones]
        if missing:
            print("N03D_BE_SOURCE_MAP_REJECT",json.dumps({"actor":actor["actor"],"rig":rig_name,
                  "missing":missing,"all_bone_names":sorted(b.name for b in rig.pose.bones)}),flush=True)
        need(not missing,"SOURCE_TARGET_BONE_NOT_PRESENT_"+rig_name)
        orig_mat=rig.matrix_world.copy()
        leg_src=(Vector(mapped_nodes["LeftKnee"]["offset"]).length+
                 Vector(mapped_nodes["LeftAnkle"]["offset"]).length)*.01
        thigh=mapping["LeftHip"];shin=mapping["LeftKnee"]
        target_len=rig.data.bones[thigh].length+rig.data.bones[shin].length
        need(.2<leg_src<2.2 and .2<target_len<2.5,"SOURCE_TARGET_LENGTH")
        ratio=target_len/leg_src
        basis=Matrix.Rotation(math.pi/2,3,"X")
        root0=source_pos(mapped_nodes["Hips"],bvh["frames"][120])
        cache={}
        for side in ("L","R"):
            observed_weighted(body,rig,mapping["LeftAnkle" if side=="L" else "RightAnkle"],cache)
        for mode in MODES:
            for b in rig.pose.bones:
                b.rotation_mode="QUATERNION"
                b.rotation_quaternion=Quaternion((1,0,0,0))
                b.location=(0,0,0)
            bpy.context.view_layer.update()
            streams={"L":[],"R":[]}
            for i in range(360):
                frame=bvh["frames"][120+i]
                for source_name,target_name in mapping.items():
                    src=basis@source_rotation(mapped_nodes[source_name],frame)@basis.inverted()
                    b=rig.pose.bones[target_name]
                    if mode=="rest_frame_conjugated":
                        rest=b.bone.matrix_local.to_3x3()
                        if b.bone.parent:
                            rest=b.bone.parent.matrix_local.to_3x3().inverted()@rest
                        src=rest.inverted()@src@rest
                    b.rotation_quaternion=src.to_quaternion()
                root_delta=basis@(source_pos(mapped_nodes["Hips"],frame)-root0)
                root_delta*=ratio*.01
                rig.matrix_world=Matrix.Translation(root_delta)@orig_mat
                bpy.context.view_layer.update()
                for side in ("L","R"):
                    key=mapping["LeftAnkle" if side=="L" else "RightAnkle"]
                    streams[side].append(observe(body,cache[key]))
            trials.append({"actor":actor["actor"],"rig":rig_name,
                           "bone_count":variant["count"],
                           "matched_rest_shape_max_deviation_m":actor["shape"]["max_rest_vertex_deviation_m"],
                           "source_motion_sha_source_git_blob":BVH_SHA1,
                           "source_frames":[120,479],"native_rate_hz":60,
                           "native_original_source_blender_pose_samples_per_side":360,
                           "mode":mode,"root_motion_leg_scale":round(ratio,6),
                           "fixed_native_body_material_foot_witness":{s:summary(x) for s,x in streams.items()},
                           "true_shoe_contact_accepted":False})
        rig.matrix_world=orig_mat
    return trials
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--source",required=True);a.add_argument("--motion",required=True)
    a.add_argument("--out",required=True)
    args=a.parse_args(sys.argv[sys.argv.index("--")+1:])
    c.validate_profiles()
    need(Path(args.source,"src/mpfb/data/3dobjs/base.obj").is_file(),"UPSTREAM_SOURCE_ABSENT")
    m=Path(args.motion).read_bytes()
    need(Path(args.motion).name=="Neutral_FW.bvh" and git_blob_sha(m)==BVH_SHA1,
         "MOTION_SOURCE_SHA_INVALID")
    bvh=parse_bvh(m)
    need(bvh["count"]==2400 and abs(bvh["frame_time"]-1/60)<1e-5,"ORIGINAL_100STYLE_TIMING")
    mapped={n["name"]:n for n in bvh["nodes"] if not n["end"]}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hs,ts,props=services()
    actors=build_pair(hs,ts,props)
    trials=[]
    for a in actors:trials.extend(actuate(a,bvh,mapped))
    shape=[{"actor":a["actor"],"profile":a["profile"],
            "default_bones":a["versions"]["default"]["count"],
            "game_engine_bones":a["versions"]["game_engine"]["count"],
            "rest_body_match":a["shape"]} for a in actors]
    out={"schema":"scp.n03d-be.identical-phenotype-two-official-MPF-rigs.v1",
         "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
         "MPFB_original_source_commit":c.UPSTREAM,
         "source_motion_blob_sha1":BVH_SHA1,
         "source_sha256":digest(m),
         "source_frames":[120,479],"source_rate_hz":60,
         "official_blender_version":list(bpy.app.version),
         "morphology_independently_measured":True,
         "shoe_asset_present":False,"source_floor_calibrated":False,
         "force_contact_verified":False,"physical_gait_accepted":False,
         "mvp_accepted":False,"status":"HOLD_PHYSICS_AND_SHOE_CONTACT",
         "morphologies":shape,"native_trials":trials}
    need(len(trials)==8 and len(shape)==2,"NO_MATCHED_RIG_NATIVE_DOE")
    Path(args.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BE_ACTUAL_IDENTICAL_MORPHOLOGY_NATIVE_RIG_DOE",
          json.dumps({"shape":shape,"trials":[{"actor":t["actor"],"rig":t["rig"],"mode":t["mode"],
                        "bones":t["bone_count"],"metrics":t["fixed_native_body_material_foot_witness"]}
                        for t in trials],"status":out["status"]},sort_keys=True),flush=True)
if __name__=="__main__":main()
