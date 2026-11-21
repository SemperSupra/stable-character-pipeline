"""N03D-BE: original-source Aster/Juniper EXACT same phenotype, default163 vs game_engine53.

Actual Blender5.2.4 official MPFB HumanService source-built bodies and true skinned
60Hz 100STYLE-constant input. Rig/morph retarget experiment, not physical support.
"""
import argparse,hashlib,importlib,json,math,struct,sys
from pathlib import Path
import bpy
from mathutils import Vector,Matrix,Quaternion
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"r078-r009-mpfb-pair"))
sys.path.insert(0,str(HERE.parent/"n03d-bd-matched-rig"))
sys.path.insert(0,str(HERE.parent/"r088-motion-real"))
import contract
import native as bd
from bvh_preflight import parse_bvh,git_blob_sha
SOURCE_BLOB="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61"
RIGS={
 "default":{"Hips":"root","LeftHip":"upperleg01.L","LeftKnee":"lowerleg01.L",
             "LeftAnkle":"foot.L","LeftToe":"toe1-1.L","RightHip":"upperleg01.R",
             "RightKnee":"lowerleg01.R","RightAnkle":"foot.R","RightToe":"toe1-1.R"},
 "game_engine":{"Hips":"pelvis","LeftHip":"thigh_l","LeftKnee":"calf_l",
                "LeftAnkle":"foot_l","LeftToe":"ball_l","RightHip":"thigh_r",
                "RightKnee":"calf_r","RightAnkle":"foot_r","RightToe":"ball_r"}
}
def need(x,why):
    if not x:raise ValueError(why)
def native_local_skin_digest(body):
    """World-root invariant actual Blender evaluated deformed local mesh fingerprint."""
    e=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m=e.to_mesh()
    try:
        need(len(m.vertices)>10000,"EMPTY_NATIVE_LOCAL_SKIN")
        step=max(1,len(m.vertices)//2048)
        h=hashlib.sha256()
        for i in range(0,len(m.vertices),step):
            h.update(struct.pack("<3f",*(round(float(z),6) for z in m.vertices[i].co)))
        return h.hexdigest()
    finally:e.to_mesh_clear()
def raw_verts(body):
    h=hashlib.sha256()
    for v in body.data.vertices:
        h.update(struct.pack("<3f",float(v.co.x),float(v.co.y),float(v.co.z)))
    return h.hexdigest()
def evaluated_profile(body):
    """Evaluated, *unmasked* shape-key-deformed body, in local mesh coordinates."""
    bpy.context.view_layer.update()
    e=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=e.to_mesh()
    try:
        need(len(mesh.vertices)>10000,"PROFILE_CORE_EVAL_EMPTY")
        h=hashlib.sha256()
        origin=e.matrix_world.translation.copy()
        points=[]
        for vert in mesh.vertices:
            world=e.matrix_world@vert.co-origin
            xyz=tuple(round(float(z),6) for z in world)
            h.update(struct.pack("<3f",*xyz))
            points.append(xyz)
        ext=[round(max(pt[k] for pt in points)-min(pt[k] for pt in points),6)
             for k in range(3)]
        return {"sha256":h.hexdigest(),"vertices":len(mesh.vertices),
                "bbox_extent_m":ext},points
    finally:e.to_mesh_clear()
def active_shape_keys(body):
    ks=body.data.shape_keys
    vals=sorted((k.name,round(float(k.value),9)) for k in ks.key_blocks) if ks else []
    data=json.dumps(vals,separators=(",",":"),ensure_ascii=True).encode()
    return {"shape_key_weight_sha256":hashlib.sha256(data).hexdigest(),
            "active_shape_key_count":sum(abs(v)>1e-9 for _,v in vals),
            "all_shape_key_count":len(vals)}
def setup():
    import addon_utils
    mod="bl_ext.user_default.mpfb"
    addon_utils.enable(mod,default_set=False,persistent=False)
    need(addon_utils.check(mod)[1],"OFFICIAL_MPF_EXTENSION_NOT_ENABLED")
    hs=importlib.import_module(mod+".services.humanservice").HumanService
    ts=importlib.import_module(mod+".services.targetservice").TargetService
    props=importlib.import_module(mod+".entities.objectproperties").HumanObjectProperties
    return hs,ts,props
def create(hs,ts,props,profile,rig_name):
    body=hs.create_human()
    need(body and body.type=="MESH","SOURCE_HUMAN_NOT_CREATED")
    for k in contract.PHENOTYPE_KEYS:
        props.set_value(k,profile[k],entity_reference=body)
    ts.reapply_macro_details(body)
    hs.refit(body)
    raw=raw_verts(body)
    # First run showed raw MakeHuman base mesh hashes can be identical even when
    # macro shape key values differ. Source morphology MUST use evaluated shape.
    excluded=[{"name":m.name,"type":m.type} for m in body.modifiers
               if m.type!="ARMATURE" and m.show_viewport]
    for m in body.modifiers:
        if m.type!="ARMATURE":m.show_viewport=False
    before,original_points=evaluated_profile(body)
    macros=active_shape_keys(body)
    bones_before=len(body.data.vertices)
    rig=hs.add_builtin_rig(body,rig_name,import_weights=True)
    need(rig is not None and rig.type=="ARMATURE","SOURCE_RIG_NOT_CREATED")
    hs.refit(body)
    rig.data.pose_position="REST"
    after,refitted_points=evaluated_profile(body)
    need(len(body.data.vertices)==bones_before and raw_verts(body)==raw,
         "MORPHOLOGY_CHANGED_AFTER_SKELETON_RAW")
    need(before["vertices"]==after["vertices"],"RIG_REFIT_TOPOLOGY_DRIFT")
    distances=[math.dist(a,b) for a,b in zip(original_points,refitted_points)]
    drift={"max_world_centered_vertex_displacement_m":round(max(distances),6),
           "rms_world_centered_vertex_displacement_m":round(
               math.sqrt(sum(x*x for x in distances)/len(distances)),6),
           "pre_and_post_evaluated_shape_identical":before["sha256"]==after["sha256"]}
    need(active_shape_keys(body)==macros,"PROFILE_MACRO_TARGETS_CHANGED_AFTER_RIG")
    body.name=profile["name"]+"_"+rig_name+"_body"
    rig.name=profile["name"]+"_"+rig_name+"_rig"
    need(any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers),
         "SOURCE_SKIN_NOT_BOUND")
    expect=163 if rig_name=="default" else 53
    need(len(rig.data.bones)==expect,"UNEXPECTED_OFFICIAL_MPF_SKELETON")
    return body,rig,raw,before,macros,excluded,after,drift
def landmarks(rig,mapping):
    coords={k:tuple(float(z) for z in rig.data.bones[mapping[k]].head_local)
            for k in ("LeftHip","LeftKnee","LeftAnkle","LeftToe","RightHip","RightKnee","RightAnkle","RightToe")}
    return coords
def measure_pair(actor,source,path):
    hs,ts,props=setup()
    profile=next((p for p in contract.PROFILES if p["name"]==actor),None)
    need(profile is not None,"UNAUTHORIZED_ACTOR_SOURCE")
    rigs={}
    for kind in ("default","game_engine"):
        body,arm,raw,shape,macros,excluded,after,drift=create(hs,ts,props,profile,kind)
        rigs[kind]={"body":body,"arm":arm,"sha":shape["sha256"],
                    "raw_sha":raw,"shape":shape,"shape_keys":macros,
                    "post_rig_shape":after,"shape_drift":drift,
                    "initial_nonarmature_exclusions":excluded,
                    "original_vertices":len(body.data.vertices),
                    "bone_count":len(arm.data.bones),
                    "landmarks":landmarks(arm,RIGS[kind])}
    need(rigs["default"]["sha"]==rigs["game_engine"]["sha"],"NOT_IDENTICAL_EVALUATED_SOURCE_MORPHOLOGY")
    need(rigs["default"]["shape"]==rigs["game_engine"]["shape"] and
         rigs["default"]["shape_keys"]==rigs["game_engine"]["shape_keys"],
         "NOT_IDENTICAL_SOURCE_MACRO_DEFORMATIONS")
    need(rigs["default"]["original_vertices"]==rigs["game_engine"]["original_vertices"],
         "BODY_TOPOLOGY_NOT_IDENTICAL")
    # Critical first-RED: MPFB native body has topology-changing display mask modifiers,
    # so evaluated topology is NOT the original material vertex index domain. For this
    # research-only comparative skin witness disable all nonarmature modifiers, retain
    # original armature deformation and verify evaluated count exactly equals source.
    # This *is not* production costume, mask, visual or sole material proof.
    ignored_modifiers={}
    for kind in ("default","game_engine"):
        body=rigs[kind]["body"]
        ignored_modifiers[kind]=rigs[kind]["initial_nonarmature_exclusions"] + [
            {"name":m.name,"type":m.type}
            for m in body.modifiers
            if m.type!="ARMATURE" and m.show_viewport]
        for m in body.modifiers:
            if m.type!="ARMATURE":m.show_viewport=False
        bpy.context.view_layer.update()
        ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        geom=ev.to_mesh()
        try:
            need(len(geom.vertices)==len(body.data.vertices),
                 "RESEARCH_ARMATURE_ONLY_MESH_TOPOLOGY_DRIFT")
        finally:ev.to_mesh_clear()
    max_joint_delta={}
    for k in rigs["default"]["landmarks"]:
        a=Vector(rigs["default"]["landmarks"][k])
        b=Vector(rigs["game_engine"]["landmarks"][k])
        max_joint_delta[k]=round((a-b).length,6)
    source_nodes=bd.get_source(source)
    conv=Matrix.Rotation(math.pi/2,3,"X")
    root0=bd.source_pos(source_nodes["Hips"],source["frames"][120])
    srcleg=(Vector(source_nodes["LeftKnee"]["offset"]).length+
            Vector(source_nodes["LeftAnkle"]["offset"]).length)*.01
    need(srcleg>.3,"SOURCE_LEG_UNIT")
    out=[]
    for kind in ("default","game_engine"):
        body=rigs[kind]["body"];arm=rigs[kind]["arm"]
        map_=RIGS[kind]
        joints=rigs[kind]["landmarks"]
        targleg=(Vector(joints["LeftHip"])-Vector(joints["LeftKnee"])).length + \
                (Vector(joints["LeftKnee"])-Vector(joints["LeftAnkle"])).length
        scale=targleg/srcleg
        need(.4<targleg<1.4 and .5<scale<2.5,"TARGET_LEG_SCALE")
        baseline=arm.matrix_world.copy()
        # WARNING first BE refit experiment sampled all source motion in REST mode;
        # that yielded the same rigid-root XY speed for every rig and both adapters.
        # Require true pose deformation and a changing body-local evaluated mesh.
        arm.data.pose_position="POSE"
        need(arm.data.pose_position=="POSE","BLENDER_POSE_EVALUATION_DISABLED")
        for mode in ("direct_canonical","rest_frame_conjugated"):
            for bone in arm.pose.bones:
                bone.rotation_mode="QUATERNION"
                bone.rotation_quaternion=Quaternion((1,0,0,0))
                bone.location=(0,0,0)
            arm.matrix_world=baseline.copy()
            bpy.context.view_layer.update()
            co=bd.cohorts([body],map_)
            need(all(co[s] for s in ("L","R")),"NO_ACTUAL_SKIN_ANKLE_TOE_WEIGHT")
            trace={"L":[],"R":[]}
            local_digest_samples={}
            for k in range(360):
                f=source["frames"][120+k]
                for n,t in map_.items():
                    srot=conv@bd.source_rotation(source_nodes[n],f)@conv.inverted()
                    if mode=="rest_frame_conjugated":
                        b=arm.data.bones[t]
                        basis=b.matrix_local.to_3x3()
                        if b.parent:basis=b.parent.matrix_local.to_3x3().inverted()@basis
                        srot=basis.inverted()@srot@basis
                    arm.pose.bones[t].rotation_quaternion=srot.to_quaternion()
                shift=conv@(bd.source_pos(source_nodes["Hips"],f)-root0)
                shift*=.01*scale
                arm.matrix_world=Matrix.Translation(shift)@baseline
                bpy.context.view_layer.update()
                if k in (0,80,160,240,359):
                    local_digest_samples[k]=native_local_skin_digest(body)
                for side in ("L","R"):trace[side].append(bd.observe_cohort(co[side]))
            need(len(set(local_digest_samples.values()))>=3,
                 "REST_MODE_OR_STALE_SKIN_FIRST_RED_DETECTED")
            reference=min(v["min_z_m"] for s in trace.values() for v in s)
            measurements={s:bd.diag(trace[s],reference) for s in ("L","R")}
            out.append({"rig":kind,"bone_count":len(arm.data.bones),"mode":mode,
                        "n_real_60hz_frames":360,"original_body_SHA256":rigs[kind]["sha"],
                        "source_frame_interval":[120,479],
                        "skin_vertex_cohorts":{s:sum(t["bottom_rest_quartile_count"] for t in co[s])
                                               for s in ("L","R")},
                        "leg_scale_ratio":round(scale,7),
                        "own_low_height_reference_not_authenticated_ground":True,
                        "actual_blender_pose_position":"POSE",
                         "native_deformed_body_local_sha256_frames":local_digest_samples,
                         "actual_local_deformed_skin_moved":True,
                         "actual_material":measurements,
                        "gait_contact_accepted":False})
    doc={"schema":"scp.n03d-be.exact-identical-morph-53-163-v1",
         "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
         "actor":actor,"mpfb_official_commit":contract.UPSTREAM,
         "original_profile":{k:profile[k] for k in contract.PHENOTYPE_KEYS},
         "source_100style_original_commit":"10938b4881b55c5801faded89e427407ddf14bce",
         "source_100style_git_blob":SOURCE_BLOB,
         "source_100style_sha256":hashlib.sha256(Path(path).read_bytes()).hexdigest(),
         "source_360_frame_clock_hz":60,"same_morphology_before_rig":True,
         "exact_source_body_mesh_sha256":rigs["default"]["sha"],
         "underlying_core_mesh_sha256":rigs["default"]["raw_sha"],
         "actual_evaluated_macro_shape":rigs["default"]["shape"],
         "shape_key_profile_fingerprint":rigs["default"]["shape_keys"],
         "post_rig_evaluated_shape_per_rig":{k:rigs[k]["post_rig_shape"] for k in rigs},
         "post_rig_shape_drift_per_rig":{k:rigs[k]["shape_drift"] for k in rigs},
         "post_rig_shape_equivalence_not_assumed":True,
         "evaluated_morphology_matched_before_rigging":True,
         "same_body_vertex_count":rigs["default"]["original_vertices"],
         "non_armature_display_modifiers_excluded":ignored_modifiers,
         "actual_material_scope":"SOURCE_BODY_ARMATURE_ONLY_FIXED_VERTEX_IDS_NOT_RENDER_MASK",
         "named_rig_joint_head_differences_m":max_joint_delta,
         "results":out,"shoe_heels_or_toe_force_verified":False,
         "true_floor_known":False,"body_anatomical_joint_centers_proven":False,
         "independent_multi_camera_visual_pass":False,
         "actor_production_identity_accepted":False,
         "mvp_accepted":False,"status":"PASS_NARROW_MORPH_MATCHED_SKIN_GEOMETRY_HOLD_CONTACT"}
    need(len(out)==4,"NOT_TWO_RIGS_TWO_MODES")
    return doc
def main():
    a=argparse.ArgumentParser()
    for n in ("actor","motion","out"):a.add_argument("--"+n,required=True)
    args=a.parse_args(sys.argv[sys.argv.index("--")+1:])
    data=Path(args.motion).read_bytes()
    need(git_blob_sha(data)==SOURCE_BLOB,"NOT_AUTHENTIC_100STYLE_MOTION")
    source=parse_bvh(data)
    need(source["count"]==2400 and abs(source["frame_time"]-1/60)<1e-5,"SOURCE_CLOCK")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    doc=measure_pair(args.actor,source,args.motion)
    Path(args.out).write_text(json.dumps(doc,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BE_TRUE_IDENTICAL_MORPH_RIG_RESULT",json.dumps({"actor":doc["actor"],
         "source_shape_sha256":doc["exact_source_body_mesh_sha256"],
         "post_rig_shape_drift":doc["post_rig_shape_drift_per_rig"],
         "rig_head_deltas":doc["named_rig_joint_head_differences_m"],
         "trials":[{"rig":t["rig"],"mode":t["mode"],"shoe":t["actual_material"],
                    "leg_scale_ratio":t["leg_scale_ratio"]} for t in doc["results"]],
         "status":doc["status"]},sort_keys=True),flush=True)
if __name__=="__main__":main()
