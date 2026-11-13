"""Measured CMU source knee-joint pole candidate on true skinned MHR frame16.

This is an independent static-frame comparative experiment with exact CMU
real 3D knee FK in disposable runner; NOT a full gait controller, and does
not publish original human motion data or derivative Blender scenes.
"""
import argparse,collections,hashlib,json,math,sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ap=argparse.ArgumentParser()
ap.add_argument("--motion",choices=("07_01","07_02"),required=True)
ap.add_argument("--source-native",type=Path,required=True)
ap.add_argument("--source-frames",type=Path,required=True)
ap.add_argument("--native-receipt",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).resolve()==a.source_native.resolve()
doc=json.loads(a.native_receipt.read_text())
assert doc["status"]=="HOLD_NATIVE_GAIT_ANATOMY_AND_CINEMATIC_VIDEO"
assert doc["original_source_motion"]==a.motion
assert doc["variant"]=="neutral"
assert doc["source_mesh_vertices"]==18439 and doc["source_rig_bones"]==126
assert doc["capture_contact_provenance"]=="UNKNOWN_NOT_FORCE_MEASURED"
assert doc["derived_full_animation_artifact_distribution"]=="WITHHELD_SOURCE_RIGHTS_VENUE_GATE"
frames=json.loads(a.source_frames.read_text())
assert len(frames)==doc["gait_frames"] and 60<=len(frames)<=67
scene=bpy.context.scene
rig=bpy.data.objects["R014_MHR_neutral_rig"]
body=bpy.data.objects["R014_MHR_neutral_body"]
assert body.parent is rig and len(body.data.vertices)==18439
foot=rig.pose.bones["r_foot"]
ik=[c for c in foot.constraints if c.type=="IK"]
assert len(ik)==1 and ik[0].chain_count==3 and not ik[0].use_stretch
con=ik[0]
assert con.pole_target is None
assert con.target is bpy.data.objects["R014_r_Go_ankle_target"]
knee=rig.pose.bones["r_lowleg"]
assert knee.parent.name=="r_upleg" or knee.parent.name.startswith("r_upleg")
side="right_leg"
source_knee=frames[15][side]["knee_relative_hipcentre_world_m"]
assert frames[15][side]["knee_jcs_interpretation"].startswith("original_CMUSOURCE")
scale=float(doc["source_to_target_leg_numeric_ratio"])
assert .65<scale<1.5
def local_mesh():
    deps=bpy.context.evaluated_depsgraph_get()
    ob=body.evaluated_get(deps)
    m=ob.to_mesh()
    try:
        inv=rig.matrix_world.inverted_safe()
        p=np.asarray([list(inv@(ob.matrix_world@v.co)) for v in m.vertices],float)
        ps=[tuple(int(i) for i in poly.vertices) for poly in m.polygons]
    finally:ob.to_mesh_clear()
    assert p.shape==(18439,3) and np.isfinite(p).all()
    return p,ps

def world_joints():
    dg=bpy.context.evaluated_depsgraph_get()
    o=rig.evaluated_get(dg)
    def head(n):return np.asarray(o.matrix_world@o.pose.bones[n].head,dtype=float)
    return {k:head(k) for k in ("r_foot","r_lowleg","r_upleg","l_upleg")}

scene.frame_set(1);bpy.context.view_layer.update()
original,polys=local_mesh()
tri=np.asarray([(p[0],p[j],p[j+1]) for p in polys for j in range(1,len(p)-1)],np.int32)
assert len(tri)==36874
def normal(p):
    v=np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]])
    return v,np.linalg.norm(v,axis=1)
n0,m0=normal(original)
assert np.min(m0)>1e-11
t=16
scene.frame_set(t);bpy.context.view_layer.update()
basej=world_joints()
old_ankle=basej["r_foot"]
native_hip_mid=.5*(basej["r_upleg"]+basej["l_upleg"])
source_offset=np.asarray([source_knee[x] for x in ("x","y","z")],float)
source_knee_target=native_hip_mid+source_offset*scale
assert np.isfinite(source_knee_target).all()
old_n,old_p=local_mesh()
assert old_p==polys
def foldovers(p):
    n,m=normal(p)
    dot=np.einsum("ij,ij->i",n0,n)
    return int(np.count_nonzero(dot<=0)),int(np.count_nonzero(m<.1*m0))
baseline_flip,baseline_collapse=foldovers(old_n)
old_count=doc["skin_geometry_samples"][str(t)]["inverted_triangles"]
assert baseline_flip==old_count,(baseline_flip,old_count)
assert baseline_flip>0
old_target=con.target.matrix_world.translation
original_pole_target=con.pole_target
original_pole_angle=float(con.pole_angle)

pole=bpy.data.objects.new("R014_SourceCMU_RealKneePole_HeldResearch",None)
bpy.context.collection.objects.link(pole)
pole.empty_display_type="SPHERE"
pole.empty_display_size=.05
pole.location=Vector(source_knee_target.tolist())
modes=[]
for angle in (0.,math.pi/2.,-math.pi/2.,math.pi,-math.pi):
    con.pole_target=pole
    con.pole_angle=angle
    bpy.context.view_layer.update()
    p,poly=local_mesh()
    assert poly==polys
    coords=world_joints()
    ank=coords["r_foot"]
    kneehead=coords["r_lowleg"]
    flip,collapse=foldovers(p)
    metrics={
       "pole_angle_rad":angle,
       "r_foot_ankle_target_residual_world":float(np.linalg.norm(ank-np.asarray(old_target,dtype=float))),
       "r_lowleg_anatomical_knee_source_target_residual_world":float(np.linalg.norm(kneehead-source_knee_target)),
       "r_foot_change_from_position_only_baseline_world":float(np.linalg.norm(ank-old_ankle)),
       "native_source_mesh_inverted_triangle_count":flip,
       "native_source_mesh_severe_collapse_count":collapse,
       "source_pose_delta_skin_vertices_gt_01_world":int(np.count_nonzero(np.linalg.norm((p-old_n)*.01,axis=1)>.01)),
    }
    modes.append(metrics)
    print("R014_REAL_SOURCE_KNEE_POLE_CANDIDATE",json.dumps({
         "motion":a.motion,"angle":angle,"ankle_error":metrics["r_foot_ankle_target_residual_world"],
         "knee_error":metrics["r_lowleg_anatomical_knee_source_target_residual_world"],
         "inversions":flip},sort_keys=True),flush=True)
con.pole_target=original_pole_target
con.pole_angle=original_pole_angle
bpy.context.view_layer.update()
restored,other=local_mesh()
assert other==polys and np.max(np.linalg.norm(restored-old_n,axis=1))<1e-5
result=[x for x in modes if x["r_foot_ankle_target_residual_world"]<.003]
best=min(result,key=lambda x:(x["native_source_mesh_inverted_triangle_count"],
                               x["r_lowleg_anatomical_knee_source_target_residual_world"])) if result else None
# No source take/derived geometry copied into public artifact.
receipt={
 "schema":"r014.cmu07.mhr_actual_knee_pole_singleframe_doe.v1",
 "status":"HOLD_SINGLE_FRAME_KNEE_POLE_RESEARCH_NOT_ANIMATED_GAIT",
 "source_motion":a.motion,
 "source_comparison_frame":16,
 "source_ground_contact":"UNKNOWN_NOT_FORCE_MEASURED",
 "source_rights_and_venue":"R012 holds adoption, original AMC/ASF/full native animation ephemeral",
 "source_3d_fk_role":"r_femur endpoint = real source knee; relative to original source hip-midpoint",
 "source_original_amc_sha256":doc["original_source_amc_sha256"],
 "target_source_rig":"official MHR v1.0.1 native Blender 126 bones, original 18439 skinned vertices",
 "source_native_animation_original_sha256_EPHEMERAL_ONLY":hashlib.sha256(a.source_native.read_bytes()).hexdigest(),
 "source_pelvis_to_knee_numeric_Blendertarget_world":source_knee_target.tolist(),
 "native_hip_mid_world":native_hip_mid.tolist(),
 "source_first_pole_source":"original measured CMU knee, no inferred contact data",
 "baseline_position_only_ik":{"inversions":baseline_flip,"severe_collapses":baseline_collapse,
    "ankle_world":old_ankle.tolist(),"ankle_target_world":list(old_target)},
 "actual_pole_candidates":modes,
 "accepted_under_ankle_only_numeric_gate":len(result),
 "least_bad_static_frame_candidate":best,
 "reversibility":"PASS_POST_CONSTRAINT_RESTORATION",
 "no_release":"SOURCE_MEASURED_NATIVE_HUMAN_GAIT_ANATOMY_CINEMATIC_HOLD",
 "limits":["Pole target directly at real CMU knee is geometric trial; source joint coordinate system/IK pole angle convention uncalibrated",
    "Single source frame only; no all-frame angular interpolation/ROM/pole target continuity",
    "Triangle inversion relative frame1 not full self-intersection/ground collision/pressure",
    "No original AMC/ASF or full-keyframed MHR/derived image public upload",
    "No complete CC0 hero GLB, calibrated morphology, hair/face/eyes/4K cinematic pass"]}
(a.out/"cmu07_source_knee_pole_scan.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
