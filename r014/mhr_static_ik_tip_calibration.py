"""R014: source-native MHR IK rest joint / bone-tip coordinate falsifier.

Test actual chain/tip semantics before introducing 169-frame Go gait, root motion,
morphology or heel/toe. One isolated side per public Actions runner.
"""
import argparse, json, math, sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ap=argparse.ArgumentParser()
ap.add_argument("--side",choices=("l","r"),required=True)
ap.add_argument("--out",type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).name=="R014_MHR_neutral_lod1.blend"
rig=bpy.data.objects["R014_MHR_neutral_rig"]
body=bpy.data.objects["R014_MHR_neutral_body"]
assert len(rig.data.bones)==126 and len(body.data.vertices)==18439
assert body.parent==rig
assert any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers)
assert "root" in rig.pose.bones
for s in ("l","r"):
    for part in ("upleg","lowleg","foot","ball"):
        assert s+"_"+part in rig.pose.bones
assert all(not b.constraints for b in rig.pose.bones)
scene=bpy.context.scene
scene.frame_set(1)
bpy.context.view_layer.update()

def bone_world(name):
    deps=bpy.context.evaluated_depsgraph_get()
    evaluated=rig.evaluated_get(deps)
    b=evaluated.pose.bones[name]
    return np.array(evaluated.matrix_world@b.head,dtype=np.float64),np.array(evaluated.matrix_world@b.tail,dtype=np.float64)

def skin():
    deps=bpy.context.evaluated_depsgraph_get()
    obj=body.evaluated_get(deps)
    mesh=obj.to_mesh()
    try:
        vertices=np.asarray([list(obj.matrix_world@v.co) for v in mesh.vertices],dtype=np.float64)
        polys=[tuple(int(k) for k in p.vertices) for p in mesh.polygons]
    finally: obj.to_mesh_clear()
    assert vertices.shape==(18439,3) and np.isfinite(vertices).all()
    return vertices,polys

baseline,polygons=skin()
tri=np.asarray([(p[0],p[j],p[j+1]) for p in polygons for j in range(1,len(p)-1)],dtype=np.int32)
assert len(tri)==36874
def normals(vertices):
    n=np.cross(vertices[tri[:,1]]-vertices[tri[:,0]],
               vertices[tri[:,2]]-vertices[tri[:,0]])
    return n,np.linalg.norm(n,axis=1)
n0,m0=normals(baseline)
assert np.min(m0)>1e-11

names=[a.side+"_"+part for part in ("upleg","lowleg","foot","ball")]
initial={n:{"head":bone_world(n)[0].tolist(),
            "tail":bone_world(n)[1].tolist(),
            "parent":rig.pose.bones[n].parent.name if rig.pose.bones[n].parent else None,
            "data_head_local":list(rig.data.bones[n].head_local),
            "data_tail_local":list(rig.data.bones[n].tail_local)}
         for n in names}
ankle_initial=np.array(initial[a.side+"_foot"]["head"])
shin_initial=np.array(initial[a.side+"_lowleg"]["tail"])
tip_gap=float(np.linalg.norm(ankle_initial-shin_initial))
print("R014_STATIC_IK_SOURCE_BONE_GEOMETRY",json.dumps({"side":a.side,"ankle_foot_head_minus_shin_tail":tip_gap,
    "bones":initial},sort_keys=True),flush=True)

def measure(name,owner,chain,target):
    bpy.context.view_layer.update()
    pos,tip=bone_world(owner.name)
    foothead,foottail=bone_world(a.side+"_foot")
    skin_now,poly_now=skin()
    assert poly_now==polygons, "source topology changed"
    n1,m1=normals(skin_now)
    bad=np.flatnonzero((np.einsum("ij,ij->i",n0,n1)<=0)|(m1<.1*m0))
    delta=np.linalg.norm(skin_now-baseline,axis=1)
    return {"case":name,"owner":owner.name,"chain_count":chain,
        "target_world":target.tolist(),
        "actual_owner_tail_world":tip.tolist(),
        "actual_ankle_foot_head_world":foothead.tolist(),
        "owner_tip_target_residual":float(np.linalg.norm(tip-target)),
        "ankle_to_target_residual":float(np.linalg.norm(foothead-target)),
        "ankle_shift_from_neutral":float(np.linalg.norm(foothead-ankle_initial)),
        "triangle_inversions":int(np.count_nonzero(np.einsum("ij,ij->i",n0,n1)<=0)),
        "severe_area_collapses":int(np.count_nonzero(m1<.1*m0)),
        "moving_skin_vertices_gt_1mm":int(np.count_nonzero(delta>.001)),
        "maximum_skin_motion_native_units":float(np.max(delta)),
        "p95_skin_motion_native_units":float(np.percentile(delta,95)),
        "sample_bad_faces":[int(i) for i in bad[:30]]}

observations=[]
control=bpy.data.objects.new("R014_IK_Test_Target_"+a.side,None)
bpy.context.collection.objects.link(control)
control.empty_display_type="SPHERE"
control.empty_display_size=.06
for part,chain in (("lowleg",2),("foot",3)):
    pb=rig.pose.bones[a.side+"_"+part]
    tip0=np.array(initial[pb.name]["tail"],dtype=np.float64)
    ankle0=ankle_initial.copy()
    con=pb.constraints.new("IK")
    con.name="R014_DISCOVERY_ONLY"
    con.target=control
    con.chain_count=chain
    con.iterations=96
    con.use_stretch=False
    for label,target in (
        ("owner_tail_at_rest",tip0),
        ("owner_tail_plus_40mm_world_x",tip0+np.array((.04,0.,0.))),
        ("ankle_foot_head_as_target",ankle0),
    ):
        control.location=Vector(target.tolist())
        bpy.context.view_layer.update()
        obs=measure(part+"_"+label,pb,chain,target)
        observations.append(obs)
        print("R014_IK_CASE",json.dumps({k:obs[k] for k in (
            "case","owner_tip_target_residual","ankle_to_target_residual",
            "triangle_inversions","severe_area_collapses",
            "maximum_skin_motion_native_units")},sort_keys=True),flush=True)
    pb.constraints.remove(con)
    bpy.context.view_layer.update()
    clean,clean_poly=skin()
    assert clean_poly==polygons
    if float(np.max(np.linalg.norm(clean-baseline,axis=1)))>.0001:
        raise ValueError("IK was not reversible after removing experimental constraint")

# Restore and preserve a single explicitly held native candidate for human review.
owner=rig.pose.bones[a.side+"_lowleg"]
con=owner.constraints.new("IK")
con.name="R014_STATIC_IK_LAST_HELD"
con.target=control
con.chain_count=2
con.iterations=96
con.use_stretch=False
control.location=Vector(ankle_initial.tolist())
bpy.context.view_layer.update()
native=a.out/("R014_MHR_"+a.side+"_static_IK_heavy_HOLD.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>100000

# Technical two-view evidence; never a gait or anatomical-quality claim.
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=5
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.render.resolution_x=320
scene.render.resolution_y=420
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
w=bpy.data.worlds.new("R014_StaticIKQA");w.use_nodes=True
w.node_tree.nodes["Background"].inputs["Strength"].default_value=.85
scene.world=w
lightdata=bpy.data.lights.new("R014_StaticIKArea","AREA")
light=bpy.data.objects.new("R014_StaticIKArea",lightdata)
bpy.context.collection.objects.link(light)
lightdata.energy=470;lightdata.size=3
camera_data=bpy.data.cameras.new("R014_StaticIKCam")
cam=bpy.data.objects.new("R014_StaticIKCam",camera_data)
bpy.context.collection.objects.link(cam)
scene.camera=cam
camera_data.type="ORTHO"
camera_data.ortho_scale=2.25
cam.location=(0,-4,1)
cam.rotation_euler=(Vector((0,0,1))-cam.location).to_track_quat("-Z","Y").to_euler()
light.location=(1.5,-2.,2.8)
scene.render.filepath=str(a.out/("ik_"+a.side+"_rest_foothead_target.png"))
bpy.ops.render.render(write_still=True)
assert Path(scene.render.filepath).stat().st_size>5000

ranked=sorted(observations,key=lambda x:(x["triangle_inversions"]+x["severe_area_collapses"],
                                       x["maximum_skin_motion_native_units"],
                                       x["owner_tip_target_residual"]))
receipt={
    "schema":"r014.mhr.static_ik_tip_calibration.v1",
    "status":"HOLD_STATIC_IK_NOT_GAIT_READY",
    "side":a.side,
    "source":"official MHR v1.0.1 FBX native 126-bone source, hash-pinned in public runner",
    "root_motion_calibration":"PR #454 exact rig object displacement passed; pose-root local had 0.01 world scale",
    "bone_geom":initial,
    "shin_tail_to_foot_head_gap":tip_gap,
    "cases":observations,
    "least_bad_case":ranked[0],
    "native_blend":native.name,
    "technical_frame":Path(scene.render.filepath).name,
    "limitations":["Owner IK tip semantics != anatomical foot head until measured",
        "No full trajectory, toe/heel contact, foot sole or human biomechanics",
        "No source glTF or full-shape body-morph acceptance",
        "No accepted adult reproductive anatomy, cinematic skin/eyes/hair or video",
        "All source MHR native units uncalibrated; synthetic adult research only"]
}
(a.out/"static_ik_tip_calibration.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_STATIC_IK_FINDINGS",json.dumps({"side":a.side,"gap":tip_gap,
       "least_bad":{k:ranked[0][k] for k in ("case","owner_tip_target_residual",
       "ankle_to_target_residual","maximum_skin_motion_native_units",
       "triangle_inversions")},"status":receipt["status"]},sort_keys=True),flush=True)
