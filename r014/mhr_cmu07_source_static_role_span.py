"""R014/W07 bridge S3 preflight: REAL source CMU07 FK meta vs native MHR rest
bone roles and geometry. No raw AMC/ASF transfer or native walking retarget.
"""
import argparse,json,math,sys
from pathlib import Path
import bpy
import numpy as np

ap=argparse.ArgumentParser()
ap.add_argument("--motion",choices=("07_01","07_02"),required=True)
ap.add_argument("--source-profile",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).name=="R014_MHR_neutral_lod1.blend"
rig=bpy.data.objects["R014_MHR_neutral_rig"]
mesh=bpy.data.objects["R014_MHR_neutral_body"]
assert len(rig.data.bones)==126 and len(mesh.data.vertices)==18439
assert len(mesh.data.shape_keys.key_blocks)==118
assert mesh.parent==rig and any(m.type=="ARMATURE" and m.object==rig for m in mesh.modifiers)
profile=json.loads(a.source_profile.read_text())
assert profile["schema"]=="motion.cmu07.original_3d_fk_profile.v1"
assert profile["status"]=="PASS_ORIGINAL_SOURCE_FK_STRUCTURAL_METADATA_ONLY"
assert profile["source_motion"]==a.motion
assert profile["source_calibrated_asf_bones"]==30
assert profile["source_fps"]==120
assert profile["original_source_amc_frames"]=={"07_01":316,"07_02":329}[a.motion]
assert profile["source_files_sha256"]["asf"]=="c29414591d76a34885bff0b04a2666bf9659f869751a2549591c55277cf95b04"
expected={
 "07_01":"3ca8e8b834481c97c32e9dd555f8c9023e33b6c52d93c9d556c83570204bf3f2",
 "07_02":"a6062c6c6bce037241d345ca8d802ab36a5cf003b60f759aa7b1db545219c065"}
assert profile["source_files_sha256"]["amc"]==expected[a.motion]
assert profile["max_bone_segment_length_residual_m"]<1e-7
dg=bpy.context.evaluated_depsgraph_get()
# Read actual source REST bones (not posed skin tip from prior experimental IK).
def rest_world(name):
    if name not in rig.data.bones:raise ValueError("source MHR bone missing: "+name)
    b=rig.data.bones[name]
    return np.asarray(rig.matrix_world@b.head_local,dtype=np.float64)
basis=np.asarray([list(r) for r in rig.matrix_world.to_3x3()],np.float64)
s=np.linalg.svd(basis,compute_uv=False)
assert .0099<s.min()<.0101 and s.max()/s.min()<1.0001
sides={}
for side in ("l","r"):
    target_names=[side+"_upleg",side+"_lowleg",side+"_foot",side+"_ball"]
    pts={n:rest_world(n) for n in target_names}
    hip,knee,ankle,ball=(pts[n] for n in target_names)
    femur=float(np.linalg.norm(hip-knee))
    shin=float(np.linalg.norm(knee-ankle))
    foot=float(np.linalg.norm(ankle-ball))
    if min(femur,shin,foot)<=.00005:raise ValueError("collapsed source MHR limb")
    source=profile["toe_proxy_profiles"][side]["source_hip_knee_ankle_numerical_lengths"]
    sf=float(source["femur_m"]);st=float(source["tibia_m"])
    assert sf>.01 and st>.01
    # Explicitly NOT a claim MHR Blender source world units are true metric m.
    # No original stature/foot arch calibration or anatomical correspondence.
    sides[side]={
      "source_cm_original_segment_lengths_publisher_m":{"femur":sf,"tibia":st},
      "native_mhr_rest_bone_role_names":target_names,
      "native_mhr_rest_joint_world_points_blender_units":{
          "hip":hip.tolist(),"knee":knee.tolist(),"ankle":ankle.tolist(),"toe_proxy":ball.tolist()},
      "native_mhr_rest_segment_lengths_blender_units":{
          "hip_to_knee":femur,"knee_to_ankle":shin,"ankle_to_ball":foot},
      "nonnormative_magnitude_ratios_target_blender_to_source_m":{
          "upper_leg_numeric_ratio":femur/sf,"lower_leg_numeric_ratio":shin/st},
      "normalized_ratio_of_ratios_dimensionless":(femur/shin)/(sf/st),
      "target_ankle_to_toe_vector_world_blender":(ball-ankle).tolist(),
      "source_fk_toe_velocity_p95_m_s":profile["source_joint_profiles"][side+"toes"]["per_frame_speed_m_s_p95"],
      "source_toe_contact_status":"UNKNOWN_NOT_FORCE_MEASURED",
      "rest_orientation_mapping_status":"NOT_QUALIFIED_AXIS_HANDEDNESS_OR_JCS"}
a0=sides["l"];b0=sides["r"]
left=a0["native_mhr_rest_segment_lengths_blender_units"];right=b0["native_mhr_rest_segment_lengths_blender_units"]
asym={k:abs(left[k]-right[k])/max(left[k],right[k]) for k in left}
if max(asym.values())>.18:raise ValueError("source native MHR bilateral skeletal rest asymmetry too large")
source_dim=[sides[s]["source_cm_original_segment_lengths_publisher_m"] for s in ("l","r")]
source_asym={k:abs(source_dim[0][k]-source_dim[1][k])/max(source_dim[0][k],source_dim[1][k]) for k in ("femur","tibia")}
if max(source_asym.values())>.2:raise ValueError("source human bilateral segment lengths implausibly different")
r={
 "schema":"r014.motion.cmu07_mhr_3d_static_role_span.v1",
 "status":"PASS_NAMED_REST_ROLE_SPANS_ONLY_NOT_NATIVE_MOTION_RETARGET",
 "source_original_motion":a.motion,
 "source_original_fk_run":43323993856,
 "source_sha256":profile["source_files_sha256"],
 "target_mhr_source_release":"facebookresearch/MHR v1.0.1",
 "target_mhr_archive_sha256":"e4f4f205cd87c0fa106577ba1de4fc763e4eb197c924461d2ef7e6944e9d6b94",
 "target_mhr_vertices":len(mesh.data.vertices),
 "target_mhr_bones":len(rig.data.bones),
 "original_target_world_to_local_basis_singular_scales":s.tolist(),
 "mapped_source_named_roles_to_target_mhr_rest":sides,
 "source_original_rest_left_right_asymmetry":source_asym,
 "target_native_mhr_rest_left_right_asymmetry":asym,
 "existing_w07_motion_schema_status":"W07 scp.walk_motion.v1 is a 2D authored synthetic fixture, NOT an original 3D ASF/AMC carrier. Any 3D source motion adapter must be separately versioned and approved by W07 owner.",
 "contact":"UNKNOWN; original CMU has joint kinematics, not measured pressure/sole/heel contact",
 "release":"R014_R009_PRODUCTION_HOLD",
 "source_data_in_artifact":"only aggregate capture metadata; no raw AMC/ASF or complete motion",
 "limitations":[
 "No actual original human recording retargeted to MHR native rig",
 "Source axes and scale into Blender Z-up not independently qualified",
 "Dimensionless morphology ratios are comparison only, not target stature/body sex/age semantics",
 "MHR rest joint names not anatomical/ROM-certified",
 "No observed ground contact, sole/heel contact or performance/cinematic gate",
 "No any actor likeness/media on public runners; owner R012 human source venue gates unchanged",
 "W07 source-neutral contract must not be silently rewritten as 3D format"],
}
out=a.out/(a.motion+".mhr_static_role_span.json")
out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
print("R014_REAL_CMUMHR_STATIC_BONE_ROLES",json.dumps({
 "motion":a.motion,
 "target_left_leg":left,
 "target_right_leg":right,
 "source_left":source_dim[0],
 "ratios":{k:sides[k]["normalized_ratio_of_ratios_dimensionless"] for k in sides},
 "status":r["status"]},sort_keys=True),flush=True)
