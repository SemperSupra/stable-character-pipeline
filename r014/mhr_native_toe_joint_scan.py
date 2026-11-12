"""R014 actual source-native MHR toe-joint actuation sensitivity on HELD gait.

Independent public synthetic, no model or biomechanical admission.
Reads actual previously saved 169-frame #458 pelvis-corrected Blender scene.
Identifies worst planted toe/ball movement and tests source foot, transverse
tarsal and ball bones as separate local FK actuators, measuring ankle custody.
"""
import argparse, json, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ap=argparse.ArgumentParser()
ap.add_argument("--side",choices=("l","r"),required=True)
ap.add_argument("--gait",type=Path,required=True)
ap.add_argument("--receipt",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
args.out.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).name=="R014_MHR_neutral_GO_GAIT_RIGGED_HOLD.blend"
go=json.loads(args.gait.read_text())
baseline=json.loads(args.receipt.read_text())
assert len(go)==169 and baseline["gait_frames"]==169
assert baseline["variant"]=="neutral"
assert baseline["status"]=="HOLD_NATIVE_GAIT_ANATOMY_AND_CINEMATIC_VIDEO"
assert baseline["source_mesh_vertices"]==18439
assert baseline["corrected_ik_end_effector"]=="foot"
assert baseline["pelvis_adjustment_world_units_applied_in_real_native_animation"] is True
assert baseline["contact"][args.side]["ankle_target_residual_max_m"]<.001
assert baseline["contact"][args.side]["actual_toe_slip_max_m"]>.07
rig=bpy.data.objects["R014_MHR_neutral_rig"]
body=bpy.data.objects["R014_MHR_neutral_body"]
assert body.parent==rig
assert len(rig.data.bones)==126 and len(body.data.vertices)==18439
assert any(m.type=="ARMATURE" and m.object is rig for m in body.modifiers)
foot=rig.pose.bones[args.side+"_foot"]
assert any(c.type=="IK" and c.chain_count==3 and c.use_rotation==False for c in foot.constraints)
targets=[args.side+"_foot",args.side+"_transversetarsal",args.side+"_ball"]
for name in targets: assert name in rig.pose.bones,name
scene=bpy.context.scene

def world_endpoints():
    deps=bpy.context.evaluated_depsgraph_get()
    erig=rig.evaluated_get(deps)
    def h(b):
        return np.array(erig.matrix_world@erig.pose.bones[b].head,dtype=np.float64)
    def t(b):
        return np.array(erig.matrix_world@erig.pose.bones[b].tail,dtype=np.float64)
    return h(args.side+"_foot"),h(args.side+"_ball"),t(args.side+"_ball")

def polygon_mesh():
    deps=bpy.context.evaluated_depsgraph_get()
    obj=body.evaluated_get(deps)
    mesh=obj.to_mesh()
    try:
        v=np.asarray([list(obj.matrix_world@p.co) for p in mesh.vertices],np.float64)
        polygons=[tuple(int(k) for k in p.vertices) for p in mesh.polygons]
    finally:obj.to_mesh_clear()
    assert v.shape==(18439,3) and np.isfinite(v).all()
    return v,polygons

contact=[bool(f["left_leg" if args.side=="l" else "right_leg"]["contact"]) for f in go]
slip=[]
for frame in range(2,170):
    if contact[frame-2] and contact[frame-1]:
        scene.frame_set(frame-1);bpy.context.view_layer.update()
        first=world_endpoints()
        scene.frame_set(frame);bpy.context.view_layer.update()
        second=world_endpoints()
        slip.append({"frame":frame,"ankle":float(np.linalg.norm(first[0]-second[0])),
                    "ball_head":float(np.linalg.norm(first[1]-second[1])),
                    "ball_tail":float(np.linalg.norm(first[2]-second[2])),
                    "previous_ball_head_world":first[1].tolist()})
assert len(slip)>30
worst=max(slip,key=lambda x:x["ball_head"])
frame=worst["frame"]
scene.frame_set(frame);bpy.context.view_layer.update()
base_ankle,base_ball,base_tip=world_endpoints()
original_vertex,polygons=polygon_mesh()
tris=np.asarray([(p[0],p[i],p[i+1]) for p in polygons for i in range(1,len(p)-1)],np.int64)
assert len(tris)==36874
def tri_norm(v):
    return np.cross(v[tris[:,1]]-v[tris[:,0]],v[tris[:,2]]-v[tris[:,0]])
restn=tri_norm(original_vertex)
restn_len=np.linalg.norm(restn,axis=1)
assert np.min(restn_len)>1e-11
previous_ball=np.array(worst["previous_ball_head_world"],np.float64)

original={name:(rig.pose.bones[name].rotation_mode,
                rig.pose.bones[name].rotation_quaternion.copy(),
                rig.pose.bones[name].rotation_euler.copy()) for name in targets}

def reset():
    for name,(mode,q,e) in original.items():
        b=rig.pose.bones[name]
        b.rotation_mode=mode
        b.rotation_quaternion=q.copy()
        b.rotation_euler=e.copy()
    bpy.context.view_layer.update()

results=[]
for bone in targets:
    for axis in range(3):
        for offset in (-.24,-.12,-.06,.06,.12,.24):
            reset()
            p=rig.pose.bones[bone]
            # The imported FBX rig uses local bone axes, not world yaw/pitch.
            # This is an actual local Euler perturbation, NOT a proof that
            # the axis is an anatomical plantar flexion control.
            p.rotation_mode="XYZ"
            e=p.rotation_euler.copy()
            e[axis]+=offset
            p.rotation_euler=e
            bpy.context.view_layer.update()
            ankle,ball,tip=world_endpoints()
            verts,new_poly=polygon_mesh()
            assert new_poly==polygons,"source mesh changed topology"
            newn=tri_norm(verts);newlen=np.linalg.norm(newn,axis=1)
            flips=int(np.count_nonzero(np.einsum("ij,ij->i",restn,newn)<=0))
            collapses=int(np.count_nonzero(newlen<.1*restn_len))
            results.append({"bone":bone,"axis":axis,"offset_rad":offset,
                "ankle_displacement_from_uncorrected_world":float(np.linalg.norm(ankle-base_ankle)),
                "toe_head_displacement_from_uncorrected_world":float(np.linalg.norm(ball-base_ball)),
                "toe_tip_displacement_from_uncorrected_world":float(np.linalg.norm(tip-base_tip)),
                "remaining_toe_head_distance_to_previous_planted_frame":float(np.linalg.norm(ball-previous_ball)),
                "original_toe_head_distance_to_previous_planted_frame":float(np.linalg.norm(base_ball-previous_ball)),
                "triangles_inverted":flips,"triangles_severely_collapsed":collapses,
                "max_skin_vertex_change_world":float(np.max(np.linalg.norm(verts-original_vertex,axis=1)))})
reset()
# A single-frame improvement is not accepted as a whole-gait result.
valid=[r for r in results if r["triangles_inverted"]==0 and
       r["triangles_severely_collapsed"]==0 and
       r["ankle_displacement_from_uncorrected_world"]<.002]
selected=min(valid,key=lambda r:r["remaining_toe_head_distance_to_previous_planted_frame"]) if valid else None
if selected:
    p=rig.pose.bones[selected["bone"]]
    p.rotation_mode="XYZ"
    e=p.rotation_euler.copy();e[selected["axis"]]+=selected["offset_rad"]
    p.rotation_euler=e
    bpy.context.view_layer.update()
native=args.out/("R014_MHR_"+args.side+"_actual_toe_actuator_held.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>100000

# This evidence is one static contact frame, not an animation acceptance.
scene.render.engine="CYCLES";scene.cycles.device="CPU";scene.cycles.samples=6
scene.render.threads_mode="FIXED";scene.render.threads=4
scene.render.resolution_x=384;scene.render.resolution_y=512
scene.render.resolution_percentage=100;scene.render.image_settings.file_format="PNG"
world=bpy.data.worlds.new("R014_toe_joint_static_QA");world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.85
scene.world=world
lightdata=bpy.data.lights.new("R014_toe_scan_area","AREA")
light=bpy.data.objects.new("R014_toe_scan_area",lightdata)
bpy.context.collection.objects.link(light)
lightdata.energy=450;lightdata.size=3
camera_data=bpy.data.cameras.new("R014_toe_scan_camera")
camera=bpy.data.objects.new("R014_toe_scan_camera",camera_data)
bpy.context.collection.objects.link(camera);scene.camera=camera
camera_data.type="ORTHO";camera_data.ortho_scale=1.5
mid=Vector(base_ankle.tolist())+Vector((0,0,.27))
camera.location=mid+Vector((.8,-2.,.5))
camera.rotation_euler=(mid-camera.location).to_track_quat("-Z","Y").to_euler()
light.location=mid+Vector((1.,-1.5,1.4))
image=args.out/("R014_MHR_"+args.side+"_toe_actuator_contact_frame.png")
scene.render.filepath=str(image)
bpy.ops.render.render(write_still=True)
assert image.stat().st_size>5000

r={"schema":"r014.mhr.toe_actuator_heldout_frame.v1",
"status":"HOLD_TOE_STATIC_ACTUATOR_NOT_ANIMATED_GAIT_OR_PHOTOREAL",
"side":args.side,"native_body_vertices":18439,"rig_bones":126,
"source_gait_run":43301146695,"source_gait_frames":169,
"source_contact_pairs":len(slip),"worst_source_contact_frame":worst,
"source_foot_world":base_ankle.tolist(),
"source_toe_head_world":base_ball.tolist(),
"source_toe_tip_world":base_tip.tolist(),
"actuators":targets,"actuator_cases":len(results),
"world_ankle_preserving_zero_inversion_cases":len(valid),
"selected_single_frame_case":selected,"all_cases":results,
"native_blend":native.name,"actual_technical_png":image.name,
"limits":["One worst source contact frame, not a full animated control",
"Local Euler actuator axes not anatomically named/qualified",
"Never alter source world-space stance ankle target or 3-link IK",
"Not pressure, ground sole friction, gait safety, body morphology or cinematic realism"] }
(args.out/"mhr_native_toe_actuator.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
print("R014_TOE_ACTUATOR_SWEEP",json.dumps({
"side":args.side,"contact_frame":frame,
"original_contact_toe_slip":worst["ball_head"],
"cases":len(results),"valid":len(valid),
"best":selected,"status":r["status"]},sort_keys=True),flush=True)
