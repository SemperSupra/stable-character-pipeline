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
    empty=bpy.data.objects.new("R014_"+side+"_Go_ankle_target",None)
    bpy.context.collection.objects.link(empty)
    empty.empty_display_size=.06
    empty.location=initial_points[side]
    targets[side]=empty
    foot=rig.pose.bones[side+"_foot"]
    constraint=foot.constraints.new("IK")
    constraint.name="R014_Research_Footbone_Three_Link_IK"
    constraint.target=empty
    constraint.chain_count=3
    constraint.iterations=64
    constraint.use_stretch=False

actuals=[]
for frame in frames:
    t=int(frame["frame"])
    assert t==len(actuals)+1
    scene.frame_set(t)
    theta=side_sign*float(frame["heading_radians"])
    rig.location=initial_loc+map_move(frame["root"])
    rig.rotation_quaternion=Quaternion((0,0,1),theta)@initial_q
    rig.keyframe_insert(data_path="location",frame=t)
    rig.keyframe_insert(data_path="rotation_quaternion",frame=t)
    for side,field in (("l","left_leg"),("r","right_leg")):
        target=initial_points[side]+map_move(subtract_dict(frame[field]["ankle"],go_init[side]))
        targets[side].location=target
        targets[side].keyframe_insert(data_path="location",frame=t)
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    evaluated=rig.evaluated_get(dg)
    record={"frame":t,"phase":frame["phase"],"root_world":list(rig.matrix_world.translation),
            "rig_yaw":theta,"legs":{}}
    for side,field in (("l","left_leg"),("r","right_leg")):
        actual=evaluated.matrix_world @ evaluated.pose.bones[side+"_foot"].head
        toe=evaluated.matrix_world @ evaluated.pose.bones[side+"_ball"].head
        target=targets[side].location
        record["legs"][side]={
            "source_contact":bool(frame[field]["contact"]),
            "ankle_world":list(actual),
            "toe_world":list(toe),
            "target_world":list(target),
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
for side in ("l","r"):
    ankle,n=foot_slip(side,"ankle_world")
    toe,_=foot_slip(side,"toe_world")
    contact[side]={"planted_pairs":n,"actual_ankle_slip_max_m":ankle,
                   "actual_toe_slip_max_m":toe,
                   "ankle_target_residual_max_m":max(x["legs"][side]["ankle_target_residual_m"] for x in actuals)}
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
    motion=np.linalg.norm(sample-rest,axis=1)
    skin[str(t)]={
        "inverted_triangles":int(np.count_nonzero(np.einsum("ij,ij->i",n0,n1)<=0)),
        "severe_area_collapse":int(np.count_nonzero(m1<.1*m0)),
        "skin_vertices_moved_over_1mm":int(np.count_nonzero(motion>.001)),
        "max_skin_motion_rig_local_m_if_units_are_metres":float(motion.max())
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
runaway_bad=any(x["max_skin_motion_rig_local_m_if_units_are_metres"] > 1.5
                for x in skin.values())
receipt={
    "status":"HOLD_NATIVE_GAIT_ANATOMY_AND_CINEMATIC_VIDEO",
    "structural_contact_candidate":not(contact_bad or foldover_bad or runaway_bad),
    "corrected_ik_end_effector":"foot",
    "corrected_ik_chain_count":3,
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
        "Sparse technical images and editable rig only; not 24fps film or photoreal 4K",
        "No human anatomy source rights/sex/age or facial/skin/hair quality acceptance"]
}
(a.out/"mhr_gait_retarget_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_REAL_RIG_GAIT",json.dumps({"variant":a.variant,"status":receipt["status"],
 "candidate":receipt["structural_contact_candidate"],"contact":contact,
 "skin":skin,"root_displacement":root_distance},sort_keys=True))
