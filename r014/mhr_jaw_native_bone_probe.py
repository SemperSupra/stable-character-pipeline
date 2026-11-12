"""R014: can actual native c_jaw bone replace inverted MHR jawDrop morph?

Experimental rigged adult synthetic mesh only; no FACS or photoreal claim.
"""
import argparse,json,math,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument("--mode",choices=("bone","coupled"),required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).name=="R014_MHR_neutral_lod1.blend"
body=bpy.data.objects["R014_MHR_neutral_body"]
rig=bpy.data.objects["R014_MHR_neutral_rig"]
assert len(body.data.vertices)==18439 and len(rig.data.bones)==126
assert body.data.shape_keys and len(body.data.shape_keys.key_blocks)==118
assert "c_jaw" in rig.pose.bones
bone=rig.pose.bones["c_jaw"]
bone.rotation_mode="XYZ"
scene=bpy.context.scene
scene.frame_set(1)
for k in body.data.shape_keys.key_blocks:
    if k.name.startswith("shape_"):k.value=0.
# The earlier factorial actual MHR QA found symmetric mouth corners safe at .35,
# and each eyelid at .25; these are experimental channels, not accepted FACS.
extras={"shape_57":.25,"shape_58":.25,"shape_77":.25,"shape_78":.25} if a.mode=="coupled" else {}
for name,value in extras.items():body.data.shape_keys.key_blocks[name].value=value
bone.rotation_euler=(0,0,0)
bpy.context.view_layer.update()

def mesh_snapshot():
    dg=bpy.context.evaluated_depsgraph_get()
    ob=body.evaluated_get(dg);mesh=ob.to_mesh()
    try:
        vertices=np.array([list(ob.matrix_world@v.co) for v in mesh.vertices],np.float64)
        polygons=[tuple(int(i) for i in f.vertices) for f in mesh.polygons]
    finally:ob.to_mesh_clear()
    assert vertices.shape==(18439,3) and np.isfinite(vertices).all()
    return vertices,polygons

# Full neutral source for absolute inversion comparator.
base,polygons=mesh_snapshot()
tri=np.array([(p[0],p[i],p[i+1]) for p in polygons for i in range(1,len(p)-1)],np.int32)
assert len(tri)==36874
neutral_n=np.cross(base[tri[:,1]]-base[tri[:,0]],base[tri[:,2]]-base[tri[:,0]])
neutral_len=np.linalg.norm(neutral_n,axis=1)
assert np.min(neutral_len)>1e-11
zlow=float(base[:,2].min());zhigh=float(base[:,2].max())
headmask=(base[tri].mean(axis=1)[:,2] >= (zlow+.73*(zhigh-zlow)))

def jawtip():
    ev=rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return ev.matrix_world@ev.pose.bones["c_jaw"].tail

baseline_tip=jawtip()
def study(case,axis,angle):
    e=[0.,0.,0.]
    if axis is not None: e[axis]=angle
    bone.rotation_euler=e
    bpy.context.view_layer.update()
    pts,polys=mesh_snapshot()
    if polys!=polygons:
        raise ValueError("source model polygon topology changed under bone rotation")
    n=np.cross(pts[tri[:,1]]-pts[tri[:,0]],pts[tri[:,2]]-pts[tri[:,0]])
    area=np.linalg.norm(n,axis=1)
    flip=np.einsum('ij,ij->i',neutral_n,n)<=0
    collapse=area < .10*neutral_len
    delta=np.linalg.norm(pts-base,axis=1)
    bad=np.flatnonzero(flip|collapse)
    return {"case":case,"axis":axis,"angle_rad":angle,
        "triangle_inversions":int(np.count_nonzero(flip)),
        "head_proxy_inversions":int(np.count_nonzero(flip&headmask)),
        "triangle_collapses":int(np.count_nonzero(collapse)),
        "moving_vertices_gt_1mm":int(np.count_nonzero(delta>.001)),
        "max_skin_motion_raw_units":float(delta.max()),
        "jaw_tip_motion_raw_units":float((jawtip()-baseline_tip).length),
        "bad_triangle_samples":[{"triangle_index":int(i),"vertex_ids":tri[i].tolist(),
          "rest_centroid":base[tri[i]].mean(axis=0).tolist()}
           for i in bad[:50]]
    }
results=[study("baseline",None,0.)]
for axis in range(3):
    for angle in (-.24,-.16,-.08,.08,.16,.24):
        results.append(study("axis"+str(axis)+"_angle"+str(angle),axis,angle))
# Head-area quality criterion structural only; 3D aesthetics remain untested.
candidates=[r for r in results[1:] if
    r["triangle_inversions"]==0 and r["triangle_collapses"]==0
    and r["moving_vertices_gt_1mm"]>=10
    and .002<=r["jaw_tip_motion_raw_units"]<=.12
    and r["max_skin_motion_raw_units"]<=.15]
chosen=(max(candidates,key=lambda x:x["jaw_tip_motion_raw_units"])
        if candidates else min(results[1:],key=lambda x:(
          x["triangle_inversions"]+x["triangle_collapses"],
          -x["jaw_tip_motion_raw_units"])))
for frame,mult in ((1,0.),(12,1.),(24,0.)):
    scene.frame_set(frame)
    e=[0.,0.,0.]
    e[chosen["axis"]]=chosen["angle_rad"]*mult
    bone.rotation_euler=e
    bone.keyframe_insert(data_path="rotation_euler",frame=frame)
bpy.context.view_layer.update()
native=a.out/("R014_"+a.mode+"_native_jaw_alternative_HELD.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>100000

scene.render.engine="CYCLES";scene.cycles.device="CPU"
scene.cycles.samples=8
scene.render.threads_mode="FIXED";scene.render.threads=4
scene.render.resolution_x=768;scene.render.resolution_y=768
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
world=bpy.data.worlds.new("R014NativeJawWorld");world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.8
scene.world=world
key=bpy.data.lights.new("R014JawSoftbox","AREA")
light=bpy.data.objects.new("R014JawSoftbox",key)
bpy.context.collection.objects.link(light)
light.location=(1.,-1.5,zhigh+.3);key.energy=350;key.size=2.0
camdata=bpy.data.cameras.new("R014JawCloseup")
cam=bpy.data.objects.new("R014JawCloseup",camdata)
bpy.context.collection.objects.link(cam)
scene.camera=cam
camdata.type="ORTHO";camdata.ortho_scale=.55
headz=zhigh-.17
cam.location=(0,-2.2,headz)
cam.rotation_euler=(Vector((0,0,headz))-cam.location).to_track_quat("-Z","Y").to_euler()
images=[]
for frame,label in ((1,"neutral"),(12,"jaw_pose")):
    scene.frame_set(frame)
    scene.render.filepath=str(a.out/(a.mode+"_"+label+"_jaw_768.png"))
    bpy.ops.render.render(write_still=True)
    assert Path(scene.render.filepath).stat().st_size>5000
    images.append(Path(scene.render.filepath).name)
receipt={
 "status":"HOLD_NATIVE_JAW_ANATOMY_AND_CINEMATIC_QUALITY",
 "source":"facebookresearch/MHR v1.0.1 official native rig",
 "source_sha256":"e4f4f205cd87c0fa106577ba1de4fc763e4eb197c924461d2ef7e6944e9d6b94",
 "mode":a.mode,"rig_bones":len(rig.data.bones),
 "mesh_vertices":len(base),"tested_axes":3,"tested_signed_joint_angles":6,
 "alternative":"real c_jaw bone rotation, not known-inverting shape_69 jawDrop",
 "extra_provisional_face_shapes":extras,"cases":results,
 "selected":chosen,"selected_zero_foldover_sample_only":chosen in candidates,
 "native_blend":native.name,"closeup_images":images,
 "limits":["Jaw tip and skin-motion measurements are not clinically correct mandibular opening",
 "No lips/teeth/tongue contact or FACS/viseme calibration",
 "No expression-specific corrective shapes, soft-tissue physics, eyes/skin/hair PBR",
 "No body morphology, real gait or 4K video quality admission",
 "Single 3D pose samples and 768px clay renders are research evidence only"]
}
(a.out/"jaw_native_bone_bakeoff_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_NATIVE_JAW_BAKEOFF",json.dumps({"mode":a.mode,
 "cases":len(results),"selected":chosen,"qualified_structure":chosen in candidates,
 "status":receipt["status"]},sort_keys=True))
