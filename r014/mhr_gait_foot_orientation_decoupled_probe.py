"""R014 corrected Blender MHR source-foot-end gait study from pinned Go IK trajectory.

Research-only experimental contact. The Go foot trajectories alone do NOT
guarantee a human body can achieve them. Never call this biometric gait proof.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Quaternion

EXPECTED_FRAMES="44d8ebb4bee9a01f522a92ff4377c4cc66c9b19df835bb4b6a1e2a847179fd56"
EXPECTED_RECEIPT="d83114db0718c059f7f6099355a50ed9db8ec62bf4df77fe63c326f39da62442"
ap=argparse.ArgumentParser()
ap.add_argument("--frames",type=Path,required=True)
ap.add_argument("--gait-receipt",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
ap.add_argument("--variant",choices=("neutral","shape20"),required=True)
ap.add_argument("--foot-orient-mode",choices=("world-fixed","stance-hold"),required=True)
a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
if hashlib.sha256(a.frames.read_bytes()).hexdigest()!=EXPECTED_FRAMES:
    raise ValueError("Go trajectory source digest drift")
if hashlib.sha256(a.gait_receipt.read_bytes()).hexdigest()!=EXPECTED_RECEIPT:
    raise ValueError("Go source receipt digest drift")
frames=json.loads(a.frames.read_text())
go=json.loads(a.gait_receipt.read_text())
assert len(frames)==169 and go["total_frames"]==169 and go["fps"]==24
assert go["status"]=="PASS_TRAJECTORY_AND_CONTACT_PROOF_ONLY"
assert go["step_events"]>=10 and go["max_planted_foot_slip_m"]<1e-7
assert Path(bpy.data.filepath).name=="R014_MHR_neutral_lod1.blend"
body=bpy.data.objects["R014_MHR_neutral_body"]
rig=bpy.data.objects["R014_MHR_neutral_rig"]
assert len(body.data.vertices)==18439 and len(rig.data.bones)==126
assert body.data.shape_keys and len(body.data.shape_keys.key_blocks)==118
assert any(m.type=="ARMATURE" and m.object is rig for m in body.modifiers)
for name in ("root","l_upleg","l_lowleg","l_foot","l_ball",
             "r_upleg","r_lowleg","r_foot","r_ball"):
    assert name in rig.pose.bones,("unrecognized source anatomy/rig control",name)
rig.animation_data_clear()
scene=bpy.context.scene
scene.render.fps=24
scene.frame_start=1
scene.frame_end=169
scene.frame_set(1)
for sk in body.data.shape_keys.key_blocks:
    if sk.name.startswith("shape_"): sk.value=0.0
if a.variant=="shape20":
    k=body.data.shape_keys.key_blocks["shape_20"]
    k.slider_min=-1.0
    k.value=.25
bpy.context.view_layer.update()

initial_matrix=rig.matrix_world.copy()
initial_loc=rig.location.copy()
initial_q=rig.rotation_quaternion.copy() if rig.rotation_mode=="QUATERNION" else rig.matrix_world.to_quaternion()
rig.rotation_mode="QUATERNION"
initial_points={}
for side in ("l","r"):
    initial_points[side]=rig.matrix_world @ rig.pose.bones[side+"_foot"].head
side_sign=-1 if initial_points["l"].x>initial_points["r"].x else 1
# Imported FBX BONE TAIL lengths may be short display/helper handles and
# are NOT necessarily the joint-to-joint anatomical segment lengths.
# Calibrate with evaluated WORLD positions of proximal hip, knee and ankle.
mhr_lengths={}
mhr_landmarks={}
for side in ("l","r"):
    hip=rig.matrix_world@rig.data.bones[side+"_upleg"].head_local
    knee=rig.matrix_world@rig.data.bones[side+"_lowleg"].head_local
    ankle=rig.matrix_world@rig.data.bones[side+"_foot"].head_local
    upper=float((knee-hip).length)
    lower=float((ankle-knee).length)
    mhr_lengths[side]=upper+lower
    mhr_landmarks[side]={"hip":list(hip),"knee":list(knee),"ankle":list(ankle),
                         "upper_m":upper,"lower_m":lower}
print("R014_WORLD_JOINT_CALIBRATION",json.dumps(mhr_landmarks,sort_keys=True),flush=True)
unit_ratio=min(mhr_lengths.values())/1.1
if not (.3<unit_ratio<1.5):
    raise ValueError("source skeletal scale outside Go trajectory assumptions")
scale=unit_ratio*.94

def map_move(obj):
    return Vector((side_sign*float(obj["y"]),-float(obj["x"]),float(obj["z"])))*scale

def subtract_dict(x,y):
    return {k:float(x[k])-float(y[k]) for k in ("x","y","z")}

go_init={"l":frames[0]["left_leg"]["ankle"],"r":frames[0]["right_leg"]["ankle"]}
targets={}
native_ik_end_effector_gap={}
source_foot_world_quat={}
for side in ("l","r"):
    # Independent static source-native IK census R014 #455:
    # MHR lowleg.tail is about 0.49048 units from the true ankle, so a
    # lowleg-tip IK target at the ankle forces massive skin deformation.
    # Foot bone has ~0.0001-unit display length and its HEAD is the ankle.
    foot_bone=rig.pose.bones[side+"_foot"]
    native_gap=float(((rig.matrix_world@foot_bone.tail)-
                      (rig.matrix_world@foot_bone.head)).length)
    if not (0.0<native_gap<.001):
        raise ValueError("MHR foot end effector no longer matches ankle head")
    native_ik_end_effector_gap[side]=native_gap
    # Exact initial source foot-bone WORLD orientation. The pinned FBX
    # rig object maps its bone-local axes through 0.01 world scale.
    source_foot_world_quat[side]=(rig.matrix_world @ foot_bone.matrix).to_quaternion()
    empty=bpy.data.objects.new("R014_"+side+"_Go_ankle_target",None)
    bpy.context.collection.objects.link(empty)
    empty.empty_display_size=.06
    empty.location=initial_points[side]
    empty.rotation_mode="QUATERNION"
    empty.rotation_quaternion=source_foot_world_quat[side].copy()
    targets[side]=empty
    foot=rig.pose.bones[side+"_foot"]
    constraint=foot.constraints.new("IK")
    constraint.name="R014_Research_Footbone_Three_Link_IK"
    constraint.target=empty
    constraint.chain_count=3
    constraint.iterations=64
    constraint.use_stretch=False
    # Preserve the #458 position-only source IK, since #459 discovered that
    # use_rotation=True overconstrains the 3-link imported FBX foot chain.
    constraint.use_rotation=False
    # Independent FOOT-BONE post-IK rotation experiment: position IK controls
    # anatomical ankle via source FBX foot.head and the following CopyRotation
    # may change only foot/children orientation. Fail closed if not true.
    copyrot=foot.constraints.new("COPY_ROTATION")
    copyrot.name="R014_PostIK_FootBone_Rotation_Research"
    copyrot.target=empty
    copyrot.owner_space="WORLD"
    copyrot.target_space="WORLD"
    copyrot.mix_mode="REPLACE"
    copyrot.influence=1.0

# Pre-solve a bounded pelvic HEIGHT adjustment against the canonical
# Go world-contact ankle targets. Preserve target world positions; DO NOT
# stretch imported FBX bone lengths or move feet along the ground to pass.
# This is a lightweight reachability corrective DoE, not biomechanics.
PELVIS_MAX_LOWERING=.20
REACH_KNEE_MARGIN=.012
raw_pelvis_lowering=[]
horizontal_unreachable={"l":[],"r":[]}
for f in frames:
    n=int(f["frame"])
    scene.frame_set(n)
    trial_heading=side_sign*float(f["heading_radians"])
    rig.location=initial_loc+map_move(f["root"])
    rig.rotation_quaternion=Quaternion((0,0,1),trial_heading)@initial_q
    for s,field in (("l","left_leg"),("r","right_leg")):
        targets[s].location=initial_points[s]+map_move(subtract_dict(f[field]["ankle"],go_init[s]))
    bpy.context.view_layer.update()
    evaluated=rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    required=0.0
    for s in ("l","r"):
        hip=evaluated.matrix_world @ evaluated.pose.bones[s+"_upleg"].head
        tgt=targets[s].location
        dx=float(hip.x-tgt.x);dy=float(hip.y-tgt.y)
        horizontal=math.hypot(dx,dy)
        admissible=mhr_lengths[s]-REACH_KNEE_MARGIN
        if horizontal>admissible:
            horizontal_unreachable[s].append(n)
        vertical_allowed=math.sqrt(max(0.0,admissible*admissible-horizontal*horizontal))
        required=max(required,max(0.0,float(hip.z-tgt.z)-vertical_allowed))
    raw_pelvis_lowering.append(required)
assert len(raw_pelvis_lowering)==169
# Noncausal 13-frame max envelope; bounded and deterministic. It anticipates
# step reach requirements to avoid moving the pelvis only AFTER losing reach.
# It does NOT enforce anatomical pelvic acceleration limits: motion remains HOLD.
pelvis_lowering=[min(PELVIS_MAX_LOWERING,
     max(raw_pelvis_lowering[max(0,i-6):min(169,i+7)]))
     for i in range(169)]
assert len(pelvis_lowering)==169
pelvis_plan={"max_required_lowering_world":max(raw_pelvis_lowering),
             "max_applied_lowering_world":max(pelvis_lowering),
             "max_interframe_lowering_change_world":max(
                (abs(pelvis_lowering[i]-pelvis_lowering[i-1])
                for i in range(1,len(pelvis_lowering))),default=0.0),
             "frames_capped":sum(x>PELVIS_MAX_LOWERING for x in raw_pelvis_lowering),
             "horizontal_unreachable_frames":horizontal_unreachable,
             "preview_window_frames":13,
             "source":"actual evaluated MHR thigh head + original MHR joint lengths, two feet",
             "world_target_custody":"unchanged original Go ankle world path, exact digest"}
print("R014_PELVIS_REACH_PREPLAN",json.dumps(pelvis_plan,sort_keys=True),flush=True)

# Explicit source-native foot orientation target controls. The all-world
# strategy is a diagnostic bound, while stance-hold only locks heading
# during actual contact intervals; neither is biomechanical gait proof.
previous_contact={"l":False,"r":False}
stance_orientation={side:source_foot_world_quat[side].copy() for side in ("l","r")}
actuals=[]
for frame in frames:
    t=int(frame["frame"])
    assert t==len(actuals)+1
    scene.frame_set(t)
    theta=side_sign*float(frame["heading_radians"])
    rig.location=initial_loc+map_move(frame["root"])+Vector((0.0,0.0,-pelvis_lowering[t-1]))
    rig.rotation_quaternion=Quaternion((0,0,1),theta)@initial_q
    rig.keyframe_insert(data_path="location",frame=t)
    rig.keyframe_insert(data_path="rotation_quaternion",frame=t)
    for side,field in (("l","left_leg"),("r","right_leg")):
        target=initial_points[side]+map_move(subtract_dict(frame[field]["ankle"],go_init[side]))
        targets[side].location=target
        targets[side].keyframe_insert(data_path="location",frame=t)
        turning_world=(Quaternion((0,0,1),theta)@source_foot_world_quat[side])
        in_contact=bool(frame[field]["contact"])
        if a.foot_orient_mode=="world-fixed":
            target_quat=source_foot_world_quat[side]
        else:
            if in_contact:
                if not previous_contact[side]:
                    stance_orientation[side]=turning_world.copy()
                target_quat=stance_orientation[side]
            else:
                target_quat=turning_world
        targets[side].rotation_quaternion=target_quat.copy()
        targets[side].keyframe_insert(data_path="rotation_quaternion",frame=t)
        previous_contact[side]=in_contact
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    evaluated=rig.evaluated_get(dg)
    record={"frame":t,"phase":frame["phase"],"root_world":list(rig.matrix_world.translation),
            "rig_yaw":theta,"legs":{}}
    for side,field in (("l","left_leg"),("r","right_leg")):
        actual=evaluated.matrix_world @ evaluated.pose.bones[side+"_foot"].head
        toe=evaluated.matrix_world @ evaluated.pose.bones[side+"_ball"].head
        hip=evaluated.matrix_world @ evaluated.pose.bones[side+"_upleg"].head
        target=targets[side].location
        hip_target_distance=float((target-hip).length)
        # The bound uses verified hip->knee + knee->ankle rest segment
        # lengths from the source-native world landmarks, NOT FBX
        # display-bone tails (see R014 #455).
        nominal_reach=mhr_lengths[side]
        record["legs"][side]={
            "source_contact":bool(frame[field]["contact"]),
            "ankle_world":list(actual),
            "toe_world":list(toe),
            "target_world":list(target),
            "hip_world":list(hip),
            "hip_to_target_world_distance":hip_target_distance,
            "nominal_hip_knee_ankle_reach":nominal_reach,
            "target_out_of_reach_excess_world":max(0.0,hip_target_distance-nominal_reach),
            "ankle_target_residual_m":float((actual-target).length)
        }
    actuals.append(record)

def foot_slip(side,member):
    distances=[]
    for prev,curr in zip(actuals,actuals[1:]):
        x=prev["legs"][side]
        y=curr["legs"][side]
        if x["source_contact"] and y["source_contact"]:
            distances.append(float((Vector(x[member])-Vector(y[member])).length))
    return max(distances,default=0.0),len(distances)

contact={}
reachability={}
for side in ("l","r"):
    ankle,n=foot_slip(side,"ankle_world")
    toe,_=foot_slip(side,"toe_world")
    contact[side]={"planted_pairs":n,"actual_ankle_slip_max_m":ankle,
                   "actual_toe_slip_max_m":toe,
                   "ankle_target_residual_max_m":max(x["legs"][side]["ankle_target_residual_m"] for x in actuals)}
    reach_series=[x["legs"][side]["target_out_of_reach_excess_world"] for x in actuals]
    reachability[side]={
        "outside_nominal_reach_count":sum(d>.001 for d in reach_series),
        "outside_nominal_reach_max_world":max(reach_series),
        "first_outside_reach_frames":[actuals[i]["frame"] for i,d in enumerate(reach_series) if d>.001][:25],
        "mean_ankle_target_error_at_unreachable_frames":(
            sum(actuals[i]["legs"][side]["ankle_target_residual_m"] for i,d in enumerate(reach_series) if d>.001)/
            max(1,sum(d>.001 for d in reach_series))
        )
    }
assert contact["l"]["planted_pairs"]>30 and contact["r"]["planted_pairs"]>30
root_distance=float((Vector(actuals[-1]["root_world"])-Vector(actuals[0]["root_world"])).length)
assert root_distance>.7

# Actual human skin mesh sampled against rest in moving rig-local coordinates.
scene.frame_set(1)
bpy.context.view_layer.update()
def skin_sample():
    dg=bpy.context.evaluated_depsgraph_get()
    e=body.evaluated_get(dg)
    mesh=e.to_mesh()
    try:
        rootinv=rig.matrix_world.inverted_safe()
        verts=np.array([list(rootinv@(e.matrix_world@v.co)) for v in mesh.vertices],np.float64)
        polys=[tuple(int(i) for i in f.vertices) for f in mesh.polygons]
    finally:
        e.to_mesh_clear()
    return verts,polys
rest,orig_polys=skin_sample()
tris=np.array([(p[0],p[i],p[i+1]) for p in orig_polys for i in range(1,len(p)-1)],np.int32)
n0=np.cross(rest[tris[:,1]]-rest[tris[:,0]],rest[tris[:,2]]-rest[tris[:,0]])
m0=np.linalg.norm(n0,axis=1)
assert np.all(np.isfinite(rest)) and np.min(m0)>1e-11
skin={}
for t in (1,40,90,130,169):
    scene.frame_set(t)
    bpy.context.view_layer.update()
    sample,polys=skin_sample()
    assert polys==orig_polys,("morph/pose changed mesh topology",t)
    n1=np.cross(sample[tris[:,1]]-sample[tris[:,0]],sample[tris[:,2]]-sample[tris[:,0]])
    m1=np.linalg.norm(n1,axis=1)
    # CRITICAL R014 corrective: the imported FBX armature matrix is
    # uniformly scaled by 0.01 relative to Blender world space.
    # Local bone units (previous 28) are NOT world metres (actual 0.28).
    basis=np.asarray([list(row) for row in rig.matrix_world.to_3x3()],np.float64)
    singular=np.linalg.svd(basis,compute_uv=False)
    if not (.0099<singular.min()<=singular.max()<.0101 and singular.max()/singular.min()<1.0001):
        raise ValueError("pinned imported MHR FBX armature world basis changed; HOLD")
    delta_local=sample-rest
    delta_world=delta_local@basis.T
    motion_world=np.linalg.norm(delta_world,axis=1)
    motion_riglocal=np.linalg.norm(delta_local,axis=1)
    skin[str(t)]={
        "inverted_triangles":int(np.count_nonzero(np.einsum("ij,ij->i",n0,n1)<=0)),
        "severe_area_collapse":int(np.count_nonzero(m1<.1*m0)),
        "skin_vertices_moved_over_1mm_world":int(np.count_nonzero(motion_world>.001)),
        "max_skin_motion_world_units":float(motion_world.max()),
        "p95_skin_motion_world_units":float(np.percentile(motion_world,95)),
        "rig_world_basis_singular_values":singular.tolist(),
        "legacy_max_rig_local_units_DO_NOT_LABEL_METRES":float(motion_riglocal.max())
    }
# Save live keyed rig, targets and all native morphs for actual editor inspection.
scene.frame_set(1)
native=a.out/("R014_MHR_"+a.variant+"_GO_GAIT_RIGGED_HOLD.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>100000

# Sparse technical stills are not cinematic gait footage.
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=5
scene.render.threads_mode="FIXED";scene.render.threads=4
scene.render.resolution_x=384;scene.render.resolution_y=512
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
world=bpy.data.worlds.new("R014_GaitTechnicalWorld");world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.9
scene.world=world
lightdata=bpy.data.lights.new("R014_GaitKey","AREA")
light=bpy.data.objects.new("R014_GaitKey",lightdata)
bpy.context.collection.objects.link(light);lightdata.energy=500;lightdata.size=3
camdata=bpy.data.cameras.new("R014_GaitCamera")
cam=bpy.data.objects.new("R014_GaitCamera",camdata)
bpy.context.collection.objects.link(cam);scene.camera=cam
camdata.type="ORTHO";camdata.ortho_scale=2.5
images=[]
for t in (1,40,90,130,169):
    scene.frame_set(t)
    bpy.context.view_layer.update()
    pos=rig.matrix_world.translation
    mid=Vector((pos.x,pos.y,0.9))
    cam.location=mid+Vector((2.0,-4.0,1.0))
    cam.rotation_euler=(mid-cam.location).to_track_quat("-Z","Y").to_euler()
    light.location=mid+Vector((1,-2,3))
    bpy.context.view_layer.update()
    filename="gait_"+a.variant+"_frame"+str(t)+".png"
    scene.render.filepath=str(a.out/filename)
    bpy.ops.render.render(write_still=True)
    assert (a.out/filename).stat().st_size>5000
    images.append(filename)
contact_bad=any(x["actual_ankle_slip_max_m"]>.04 or x["actual_toe_slip_max_m"]>.05 or
                x["ankle_target_residual_max_m"]>.06 for x in contact.values())
foldover_bad=any(x["inverted_triangles"] or x["severe_area_collapse"] for x in skin.values())
# Fail closed on true excessive WORLD-coordinate motion, not imported
# FBX bone-local units. The previous threshold of 1.5 rig-local units
# equals only 0.015 world units and falsely rejected normal leg motion.
runaway_bad=any(x["max_skin_motion_world_units"] > 1.0
                for x in skin.values())
reach_bad=any(x["outside_nominal_reach_max_world"]>.02 for x in reachability.values())
receipt={
    "status":"HOLD_NATIVE_GAIT_ANATOMY_AND_CINEMATIC_VIDEO",
    "structural_contact_candidate":not(contact_bad or foldover_bad or runaway_bad or reach_bad),
    "coordinate_system_correction":"Legacy rig-local deformation magnitudes divided by 100 through verified MHR FBX matrix to Blender world coordinates",
    "native_rig_world_scale":0.01,
    "reachability":reachability,
    "reachability_gate_holds":reach_bad,
    "pelvis_vertical_reach_preplan":pelvis_plan,
    "pelvis_adjustment_world_units_applied_in_real_native_animation":True,
    "corrected_ik_end_effector":"foot",
    "corrected_ik_chain_count":3,
    "foot_orientation_mode":a.foot_orient_mode,
    "ik_target_rotation_constraint_enabled":False,
    "separate_copy_rotation_constraint":"R014_PostIK_FootBone_Rotation_Research",
    "decoupled_foot_bone_world_copy_rotation_enabled":True,
    "constraint_evaluation_warning":"Post-IK foot rotation is experimental and can perturb ankle reach; actual residual and mesh geometry decide.",
    "source_foot_world_quaternions":{k:list(v) for k,v in source_foot_world_quat.items()},
    "ik_end_effector_to_ankle_source_gap_native":native_ik_end_effector_gap,
    "independent_static_ik_support":"R014 draft PR #455, public run 43298141785, two side-specific trials",
    "runaway_skin_motion_detected":runaway_bad,
    "variant":a.variant,
    "source_model":"official pinned MHR v1.0.1 Blender LOD1",
    "source_gait":"public Go world-foot math run 43246188313, not real motion source",
    "source_gait_frames_sha256":EXPECTED_FRAMES,
    "source_gait_receipt_sha256":EXPECTED_RECEIPT,
    "mhr_model_release_sha256":"e4f4f205cd87c0fa106577ba1de4fc763e4eb197c924461d2ef7e6944e9d6b94",
    "source_mesh_vertices":len(rest),"source_rig_bones":len(rig.data.bones),
    "gait_frames":len(frames),"gait_root_world_displacement_m_if_units_are_metres":root_distance,
    "mhr_to_go_leg_scale":scale,"native_joint_chain_lengths":mhr_lengths,"native_joint_world_landmarks":mhr_landmarks,
    "mapping_side_sign":side_sign,
    "contact":contact,"skin_geometry_samples":skin,"native_blend":native.name,
    "rendered_sparse_frames":images,
    "limitations":["Go planner IK is mathematical source only; corrected foot-tip target solver on MHR can still fail/slide",
        "Single morphology slider variation does not recalibrate bone lengths or mass",
        "Foot bone/ball proxies are not direct vertex pad or sole/ground collision",
        "No heel-toe roll, calibrated joint ROM, hip weight transfer, self-collision or realism review",
        "Separate CopyRotation after position-only IK is experimental; no guarantee of truly independent kinematics",
        "World-rotation IK target is a bounded experimental contact pose, not a physically qualified toe-roll gait",
        "Pelvis height is a bounded geometric reach controller; noncausal lookahead and no pelvis acceleration/body-mass physics",
        "Earlier #456 rig-local skin displacement mislabeling was a factor 100 FBX coordinate error; preserved as negative control",
        "Sparse technical images and editable rig only; not 24fps film or photoreal 4K",
        "No human anatomy source rights/sex/age or facial/skin/hair quality acceptance"]
}
(a.out/"mhr_gait_retarget_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_REAL_RIG_GAIT",json.dumps({"variant":a.variant,"status":receipt["status"],
 "candidate":receipt["structural_contact_candidate"],"contact":contact,
 "foot_orientation_mode":a.foot_orient_mode,
 "skin":skin,"root_displacement":root_distance},sort_keys=True))
