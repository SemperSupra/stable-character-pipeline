"""R014 full source-native MHR toe/contact controller evaluation.

Reuses verified held Blender native MHR gait (PR #463) and exact public
original Go contact frames. Experimental toe/ball joint source geometry only.
No protected human identity or unadmitted real mocap source.
"""
import argparse, json, sys
from pathlib import Path

import bpy
from mathutils import Vector
import numpy as np

ap=argparse.ArgumentParser()
ap.add_argument("--variant", choices=("neutral","shape20"),required=True)
ap.add_argument("--target", choices=("ball-head","ball-tip"),required=True)
ap.add_argument("--frames", type=Path,required=True)
ap.add_argument("--source-receipt",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).name=="R014_MHR_neutral_GO_GAIT_RIGGED_HOLD.blend"
go=json.loads(a.frames.read_text())
original=json.loads(a.source_receipt.read_text())
assert len(go)==169 and original["gait_frames"]==169
assert original["variant"]==a.variant and original["source_mesh_vertices"]==18439
assert original["source_rig_bones"]==126
assert original["status"]=="HOLD_NATIVE_GAIT_ANATOMY_AND_CINEMATIC_VIDEO"
assert original["pelvis_slope_control_verified"] is True
assert original["pelvis_vertical_reach_preplan"]["max_interframe_lowering_change_world"] < .0080001
assert original["corrected_ik_chain_count"]==3
rig=bpy.data.objects["R014_MHR_neutral_rig"]
body=bpy.data.objects["R014_MHR_neutral_body"]
assert body.parent is rig and len(body.data.vertices)==18439
assert len(rig.pose.bones)==126
scene=bpy.context.scene
scene.frame_start=1;scene.frame_end=169;scene.render.fps=24
side_map={"l":"left_leg","r":"right_leg"}
bones={s:rig.pose.bones[s+"_foot"] for s in side_map}
for s,p in bones.items():
    assert any(c.type=="IK" and c.chain_count==3 and not c.use_rotation for c in p.constraints)
    assert s+"_ball" in rig.pose.bones
    assert "R014_"+s+"_Go_ankle_target" in bpy.data.objects
    # This controls source-local foot axial rotation, not anatomically
    # identified pitch/roll. Preregister previous 54-case source evidence.
assert original["contact"]["l"]["ankle_target_residual_max_m"]<.001
assert original["contact"]["r"]["ankle_target_residual_max_m"]<.001

def locs(s):
    dg=bpy.context.evaluated_depsgraph_get()
    erig=rig.evaluated_get(dg)
    bone=erig.pose.bones[s+"_ball"]
    fb=erig.pose.bones[s+"_foot"]
    return (
        np.asarray(erig.matrix_world@fb.head,dtype=np.float64),
        np.asarray(erig.matrix_world@bone.head,dtype=np.float64),
        np.asarray(erig.matrix_world@bone.tail,dtype=np.float64),
    )

def evaluated_mesh():
    dg=bpy.context.evaluated_depsgraph_get()
    e=body.evaluated_get(dg)
    mesh=e.to_mesh()
    try:
        v=np.asarray([list(e.matrix_world@x.co) for x in mesh.vertices],np.float64)
        polys=[tuple(int(i) for i in p.vertices) for p in mesh.polygons]
    finally:
        e.to_mesh_clear()
    return v,polys

# Original source animation contains no authored foot-local angular keys.
# Explicitly set Euler mode and key a zero-relative toe actuator at *every*
# frame, including swing, while retaining original rig object/goal FCurves.
base_euler={}
for s,p in bones.items():
    scene.frame_set(1)
    original_q=p.rotation_quaternion.copy()
    if p.rotation_mode=="QUATERNION":
        base_euler[s]=original_q.to_euler("XYZ")
    elif p.rotation_mode=="XYZ":
        base_euler[s]=p.rotation_euler.copy()
    else:
        raise ValueError("unexpected source foot orientation channel")
    p.rotation_mode="XYZ"
    p.rotation_euler=base_euler[s].copy()

contacts={s:[bool(f[side_map[s]]["contact"]) for f in go] for s in side_map}
anchors={s:None for s in side_map}
previous={s:0.0 for s in side_map}
angles={s:[] for s in side_map}
records={s:[] for s in side_map}
MAX_ANGLE=.48
MAX_STEP=.14
for frame in range(1,170):
    scene.frame_set(frame)
    # Explicitly force evaluated pose to the intended outgoing actuator
    # baseline, avoiding dependence on Blender action interpolation.
    for s,p in bones.items():
        p.rotation_euler=base_euler[s].copy()
    bpy.context.view_layer.update()
    for s,p in bones.items():
        is_stance=contacts[s][frame-1]
        last_stance=contacts[s][frame-2] if frame>1 else False
        toe_idx=1 if a.target=="ball-head" else 2
        before=locs(s)
        if is_stance and not last_stance:
            anchors[s]=before[toe_idx].copy()
            previous[s]=0.0
        if not is_stance:
            anchors[s]=None
            # Return locally and smoothly to the source neutral foot axis.
            theta=max(-MAX_STEP,min(MAX_STEP,-previous[s]))+previous[s]
        else:
            # 1D constrained local source-foot actuator search:
            # preserve original world ankle, hold observed ball contact,
            # penalize abrupt toe-local angles and no invented bone length.
            desired=anchors[s]
            assert desired is not None
            low=max(-MAX_ANGLE,previous[s]-MAX_STEP)
            high=min(MAX_ANGLE,previous[s]+MAX_STEP)
            values=[low+(high-low)*k/10.0 for k in range(11)]
            if low<=previous[s]<=high:values.append(previous[s])
            baseline=before[0]
            best=None
            for value in values:
                e=base_euler[s].copy();e[2]+=value
                p.rotation_euler=e
                bpy.context.view_layer.update()
                ankle,head,tip=locs(s)
                point=head if toe_idx==1 else tip
                ankle_error=float(np.linalg.norm(ankle-baseline))
                if ankle_error>.002: continue
                deviation=float(np.linalg.norm(point-desired))
                # All distances in Blender WORLD units; the angle regularizer
                # is explicitly heuristic, not a biomechanical objective.
                score=deviation+.008*abs(value-previous[s])+.001*abs(value)
                item=(score,value,deviation,ankle_error)
                if best is None or item<best:best=item
            if best is None:
                theta=previous[s]
            else:
                theta=best[1]
        e=base_euler[s].copy();e[2]+=theta
        p.rotation_euler=e
        p.keyframe_insert(data_path="rotation_euler",frame=frame,group="R014_research_foot_contact")
        bpy.context.view_layer.update()
        ankle,head,tip=locs(s)
        target=bpy.data.objects["R014_"+s+"_Go_ankle_target"].location
        ankle_error=float(np.linalg.norm(ankle-np.asarray(target,dtype=np.float64)))
        records[s].append({
            "frame":frame,"contact":is_stance,"angle_source_local_z":theta,
            "ankle_world":ankle.tolist(),
            "ball_head_world":head.tolist(),"ball_tip_world":tip.tolist(),
            "ankle_target_error_world":ankle_error,
            "toe_anchor_error_world":(float(np.linalg.norm((head if toe_idx==1 else tip)-anchors[s]))
                                        if is_stance else None),
        })
        angles[s].append(theta)
        previous[s]=theta

# AFTER all real Blender keyframes, independently REOPEN animation channel
# at each original frame, so the measured motion is the saved FCurve result.
checked={s:[] for s in side_map}
for frame in range(1,170):
    scene.frame_set(frame);bpy.context.view_layer.update()
    for s in side_map:
        ank,h,t=locs(s)
        target=bpy.data.objects["R014_"+s+"_Go_ankle_target"].location
        checked[s].append((ank,h,t,float(np.linalg.norm(ank-np.asarray(target,dtype=np.float64)))))
metrics={}
for s in side_map:
    ankle_slip=[];toe_head_slip=[];toe_tip_slip=[]
    source=records[s]
    for idx in range(1,169):
        if contacts[s][idx] and contacts[s][idx-1]:
            before=checked[s][idx-1];after=checked[s][idx]
            ankle_slip.append(float(np.linalg.norm(before[0]-after[0])))
            toe_head_slip.append(float(np.linalg.norm(before[1]-after[1])))
            toe_tip_slip.append(float(np.linalg.norm(before[2]-after[2])))
    assert len(ankle_slip)==108
    metrics[s]={
      "source_toe_slip_max_world":original["contact"][s]["actual_toe_slip_max_m"],
      "observed_ankle_target_max_world":max(x[3] for x in checked[s]),
      "observed_ankle_slip_max_world":max(ankle_slip),
      "observed_ball_head_slip_max_world":max(toe_head_slip),
      "observed_ball_tip_slip_max_world":max(toe_tip_slip),
      "original_source_control_max_angle_rad":max(abs(x) for x in angles[s]),
      "source_actuator_max_angle_first_difference":max(abs(angles[s][i]-angles[s][i-1]) for i in range(1,169)),
      "contact_pairs":len(ankle_slip),
      "angular_series":[round(x,8) for x in angles[s]]
    }

# Scan selected skinned full-body poses for foldover/collapse. Not all 169.
base_body=None;tri=None;ref_n=None;ref_len=None;skin={}
for frame in (1,28,40,90,130,169):
    scene.frame_set(frame);bpy.context.view_layer.update()
    verts,polys=evaluated_mesh()
    if base_body is None:
        base_body=verts
        tri=np.asarray([(p[0],p[k],p[k+1]) for p in polys for k in range(1,len(p)-1)],np.int64)
        assert len(tri)==36874
        ref_n=np.cross(base_body[tri[:,1]]-base_body[tri[:,0]],base_body[tri[:,2]]-base_body[tri[:,0]])
        ref_len=np.linalg.norm(ref_n,axis=1)
    else:
        assert all(len(p)>2 for p in polys)
        n=np.cross(verts[tri[:,1]]-verts[tri[:,0]],verts[tri[:,2]]-verts[tri[:,0]])
        mag=np.linalg.norm(n,axis=1)
        skin[str(frame)]={
          "inverted_triangles":int(np.count_nonzero(np.einsum("ij,ij->i",ref_n,n)<=0)),
          "severe_area_collapse":int(np.count_nonzero(mag<.1*ref_len)),
          "max_relative_skin_change_world":float(np.max(np.linalg.norm(verts-base_body,axis=1)))}
fail_geometry=any(x["inverted_triangles"] or x["severe_area_collapse"] for x in skin.values())
fail_ankle=any(m["observed_ankle_target_max_world"]>.003 or m["observed_ankle_slip_max_world"]>.003 for m in metrics.values())
fail_toe=any(m["observed_ball_head_slip_max_world"]>.035 for m in metrics.values())
candidate=not (fail_geometry or fail_ankle or fail_toe)
# Candidate is ONLY structural; realism, footpad contact and source-rights still HOLD.
scene.frame_set(1)
native=a.out/("R014_MHR_"+a.variant+"_"+a.target+"_toe_controller_HOLD.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>100000

scene.render.engine="CYCLES";scene.cycles.device="CPU";scene.cycles.samples=6
scene.render.threads_mode="FIXED";scene.render.threads=4
scene.render.resolution_x=320;scene.render.resolution_y=420
scene.render.resolution_percentage=100;scene.render.image_settings.file_format="PNG"
framesout=[]
for f in (28,40):
    scene.frame_set(f)
    out=a.out/("R014_"+a.target+"_"+a.variant+"_frame"+str(f)+".png")
    scene.render.filepath=str(out);bpy.ops.render.render(write_still=True)
    assert out.stat().st_size>5000
    framesout.append(out.name)
receipt={
  "schema":"r014.mhr.toe_contact_full169.v1",
  "status":"PASS_TECHNICAL_TOE_CONTACT_ONLY_NOT_CINEMATIC" if candidate else "HOLD_REAL_GAIT_TOE_CONTACT_OR_GEOMETRY",
  "release_status":"R014_AND_R009_PRODUCTION_HOLD",
  "source_run":43319201041,"variant":a.variant,"toe_target_strategy":a.target,
  "source_model":"official MHR native FBX v1.0.1, no protected identity",
  "motion_source":"169 original Go contact frames NOT real mocap",
  "source_model_rig_bones":126,"source_mesh_vertices":18439,
  "frame_count":169,"contact_provenance":"SOURCE_ORIGINAL_SYNTHETIC_GAIT_ANNOTATION_NOT_FORCE_MEASURED",
  "toe_local_actuator":"MHR native foot bone local rotation_euler axis 2, anatomical sign UNKNOWN",
  "limits":{"max_foot_angle_rad":MAX_ANGLE,"max_step_angle_rad":MAX_STEP,
            "ankle_world_error_gate":.003,"toe_head_world_step_gate":.035},
  "full_sequence_results":metrics,"skin_qa_sampled_frames":skin,
  "geometry_fail":bool(fail_geometry),"ankle_fail":bool(fail_ankle),"toe_fail":bool(fail_toe),
  "native_blend":native.name,"technical_pngs":framesout,
  "nonadmission":["No real source CMU capture or measured biomechanics",
    "No ground sole/heel/toe pressure or signed contact force",
    "Pelvis smooth first derivative only, no accel/jerk physiological gate",
    "Skin topology checked at selected frames not every frame",
    "Morph shape20 opaque uncalibrated, not broad anthropometric qualification",
    "No material/hair/eyes/teeth/face/full detailed anatomy photoreal qualification"]}
(a.out/"r014_mhr_toe_full169.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_REAL_TOE_FULL169",json.dumps({k:receipt[k] for k in
("status","variant","toe_target_strategy","full_sequence_results","skin_qa_sampled_frames")},sort_keys=True),flush=True)
