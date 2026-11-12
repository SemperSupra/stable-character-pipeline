"""R014 native MHR: pose/face actuated LOD1 + authored subdivision experiment.

Actual FBX-derived rig and morphs in a fresh-reopened Blender scene.
A modifier subdivision is NOT high-frequency sculpt detail or MHR nonlinear inference.
"""
import argparse, json, math, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

p=argparse.ArgumentParser()
p.add_argument("--out",required=True,type=Path)
p.add_argument("--mode",choices=("arm","face"),required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
body=bpy.data.objects["R014_MHR_neutral_body"]
rig=bpy.data.objects["R014_MHR_neutral_rig"]
assert body.type=="MESH" and rig.type=="ARMATURE"
assert len(body.data.vertices)>10000 and len(rig.data.bones)>20
assert body.data.shape_keys and len(body.data.shape_keys.key_blocks)==118
assert any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers)
assert bpy.data.filepath and bpy.data.is_saved

names=[b.name for b in rig.pose.bones]
candidate=[x for x in names if
    ("upperarm" in x.lower() or "upper_arm" in x.lower() or
     "shoulder" in x.lower() or "clavicle" in x.lower() or
     ("arm" in x.lower() and not any(t in x.lower() for t in ("fore","lower","hand"))))]
arm_name=sorted(candidate,key=lambda n: (not (".l" in n.lower() or "left" in n.lower()),len(n)))[0] if candidate else None
if a.mode=="arm" and not arm_name:
    raise ValueError("MHR rig arm bone unrecognized: "+repr(names[:90]))
controls={
    "shape_57":("eyeBlinkLeft",.50),
    "shape_58":("eyeBlinkRight",.50),
    "shape_69":("jawDrop",.50),
    "shape_77":("lipCornerPullerLeft",.35),
    "shape_78":("lipCornerPullerRight",.35)
}
for key in controls:
    assert key in body.data.shape_keys.key_blocks
subsurf=body.modifiers.new("R014_Subdivision_For_Cinematic_Pipeline_HOLD","SUBSURF")
subsurf.subdivision_type="CATMULL_CLARK"
subsurf.levels=0
subsurf.render_levels=0
subsurf.show_render=True
scene=bpy.context.scene
scene.frame_start=1
scene.frame_end=24
scene.render.fps=24

for pb in rig.pose.bones:
    pb.rotation_mode="XYZ"

def configure(frame, active):
    scene.frame_set(frame)
    for key,(semantic,amplitude) in controls.items():
        k=body.data.shape_keys.key_blocks[key]
        k.value=amplitude if a.mode=="face" and active else 0.
        k.keyframe_insert(data_path="value",frame=frame)
    if arm_name:
        b=rig.pose.bones[arm_name]
        b.rotation_euler=(.3 if a.mode=="arm" and active else 0,0,0)
        b.keyframe_insert(data_path="rotation_euler",frame=frame)
    bpy.context.view_layer.update()

for frame,active in ((1,False),(12,True),(24,False)):
    configure(frame,active)

def measured_mesh(level,frame):
    scene.frame_set(frame)
    subsurf.levels=level
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    ev=body.evaluated_get(dg)
    mesh=ev.to_mesh()
    try:
        arr=np.asarray([list(ev.matrix_world@v.co) for v in mesh.vertices],dtype=np.float64)
        # Keep face topology independent of Blender's geometry-dependent
        # quad diagonal choices. A morph can rotate a diagonal in a quad even
        # though its vertex/polygon connectivity stays exactly unchanged.
        # Index-fan triangulation is deterministic across poses and is used
        # ONLY for deformation QA (not an exported tessellation assertion).
        faces=np.asarray([
            (int(poly.vertices[0]),int(poly.vertices[j]),int(poly.vertices[j+1]))
            for poly in mesh.polygons
            for j in range(1,len(poly.vertices)-1)
        ],dtype=np.int64)
    finally:
        ev.to_mesh_clear()
    if not np.isfinite(arr).all() or not len(faces):
        raise ValueError("invalid evaluated MHR mesh")
    return arr,faces

def qa(rest,posed,faces):
    if rest.shape!=posed.shape:
        raise ValueError("topology / vertex count changed under pose")
    verts=faces
    n0=np.cross(rest[verts[:,1]]-rest[verts[:,0]],
                rest[verts[:,2]]-rest[verts[:,0]])
    n1=np.cross(posed[verts[:,1]]-posed[verts[:,0]],
                posed[verts[:,2]]-posed[verts[:,0]])
    mag0=np.linalg.norm(n0,axis=1)
    mag1=np.linalg.norm(n1,axis=1)
    mask=mag0>1e-11
    flip=mask & (np.einsum("ij,ij->i",n0,n1)<=0)
    collapse=mask & (mag1 < .1*mag0)
    motion=np.linalg.norm(posed-rest,axis=1)
    return {
        "vertices":int(len(rest)),
        "triangles":int(len(faces)),
        "inversions":int(flip.sum()),
        "severe_area_collapses":int(collapse.sum()),
        "degenerate_rest_triangles":int((~mask).sum()),
        "moving_vertices_over_1mm":int((motion>.001).sum()),
        "max_motion_m_if_mhr_units_are_metres":float(motion.max()),
        "p95_motion_m_if_mhr_units_are_metres":float(np.percentile(motion,95)),
        "rest_bounds_raw":(rest.max(axis=0)-rest.min(axis=0)).tolist(),
    }

results={}
for level in (0,1,2):
    neutral,tri=measured_mesh(level,1)
    posed,tri_pose=measured_mesh(level,12)
    if not np.array_equal(tri,tri_pose):
        raise ValueError("face ordering changed at same subdivision level")
    results[str(level)]=qa(neutral,posed,tri)
    assert results[str(level)]["vertices"]>10000
assert results["2"]["vertices"]>results["1"]["vertices"]>results["0"]["vertices"]
assert results["0"]["moving_vertices_over_1mm"]>50,("no motion",results["0"])
neutral,faces=measured_mesh(0,1)
posed,_=measured_mesh(0,12)

# Preserve source-native modifier and animations. glTF is a lower-fidelity
# interchange candidate and may not include live MHR neural pose correctives.
subsurf.levels=0
subsurf.render_levels=0
scene.frame_set(1)
native=a.out/("R014_MHR_"+a.mode+"_subdiv_motion_held.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>100000

subsurf.levels=1
subsurf.render_levels=1  # Render real evaluated subdivision; not authored detail.
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=4
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.render.resolution_x=384
scene.render.resolution_y=512
scene.render.resolution_percentage=100
world=bpy.data.worlds.new("R014_Native_MHR_Motion_Study")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.9
scene.world=world
lampdata=bpy.data.lights.new("R014_MHR_Study_Key","AREA")
lamp=bpy.data.objects.new("R014_MHR_Study_Key",lampdata)
bpy.context.collection.objects.link(lamp)
lampdata.energy=550;lampdata.size=3
camera=bpy.data.cameras.new("R014_MHR_Study_Camera")
cam=bpy.data.objects.new("R014_MHR_Study_Camera",camera)
bpy.context.collection.objects.link(cam)
scene.camera=cam
camera.type="ORTHO"
both=np.concatenate([neutral,posed],axis=0)
lo=both.min(axis=0)
hi=both.max(axis=0)
mid=(lo+hi)*.5
ext=hi-lo
camera.ortho_scale=max(float(ext[2]*1.27),float(ext[0])/(384/512)*1.28,1.8)
cam.location=(float(mid[0]),float(mid[1]-max(4,ext[1]*4)),float(mid[2]))
cam.rotation_euler=(Vector(mid.tolist())-cam.location).to_track_quat("-Z","Y").to_euler()
lamp.location=(float(mid[0]+1.5),float(mid[1]-2.0),float(mid[2]+2))
bpy.context.view_layer.update()
def bounds_on_cam(arr):
    v=[world_to_camera_view(scene,cam,Vector(p.tolist())) for p in arr]
    q=np.array([[w.x,w.y,w.z] for w in v])
    return q.min(axis=0),q.max(axis=0)
coverage={}
for name,arr in (("neutral",neutral),("pose",posed)):
    low,high=bounds_on_cam(arr[::20])
    if np.any(low[:2]<=0) or np.any(high[:2]>=1) or low[2]<=0:
        raise ValueError("camera does not frame actual body "+name)
    coverage[name]={"min":low.tolist(),"max":high.tolist()}

for frame,name in ((1,"neutral"),(12,"pose")):
    scene.frame_set(frame)
    scene.render.image_settings.file_format="PNG"
    scene.render.filepath=str(a.out/(a.mode+"_"+name+".png"))
    bpy.ops.render.render(write_still=True)
    assert Path(scene.render.filepath).stat().st_size>5000

scene.render.image_settings.file_format="FFMPEG"
scene.render.ffmpeg.format="MPEG4"
scene.render.ffmpeg.codec="H264"
scene.render.filepath=str(a.out/("R014_MHR_"+a.mode+"_real_rig_motion_technical.mp4"))
bpy.ops.render.render(animation=True)
video=Path(scene.render.filepath)
assert video.stat().st_size>1000

# Export the actual source mesh/rig. Blender modifier is *not* guaranteed
# portable at the native evaluated subdivision; report base GLB only.
scene.frame_set(1)
subsurf.levels=0
subsurf.render_levels=0  # Portable GLB is explicitly base LOD1, no native subdiv claim.
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active=body
gltf=a.out/("R014_MHR_"+a.mode+"_base_LOD1_motion.glb")
bpy.ops.export_scene.gltf(filepath=str(gltf),export_format="GLB",
                          use_selection=True,export_morph=True,export_skins=True,
                          export_animations=True,export_yup=True,
                          )
assert gltf.stat().st_size>100000

receipt={
    "schema":"r014.mhr.native.motion.subdiv.v1",
    "status":"HOLD_CINEMATIC_AND_ANATOMICAL_QUALIFICATION",
    "source":"facebookresearch/MHR v1.0.1 official LOD1 native Blender",
    "source_archive_sha256":"e4f4f205cd87c0fa106577ba1de4fc763e4eb197c924461d2ef7e6944e9d6b94",
    "mode":a.mode,"arm_bone":arm_name,
    "rig_bones":len(rig.data.bones),"source_keyblocks":len(body.data.shape_keys.key_blocks),
    "pose_samples":{"neutral":1,"posed":12,"return":24},
    "subdivision_levels":results,
    "triangle_oracle":"DETERMINISTIC_POLYGON_INDEX_FAN; not Blender adaptive loop triangulation or UV/artistic quality",
    "topology_assertion":"stable vertex indices and per-polygon ordered vertex membership at each level",

    "camera":coverage,
    "native_blend":native.name,"base_rig_glb":gltf.name,"actual_motion_mp4":video.name,
    "constraints":["Subdivision is geometric smoothness NOT authentic sculpt pores or skin microdetails",
        "Only sampled arm or facial motion; not qualified full body kinetics or FACS",
        "No proof GLB reproduces native neural pose correctives / high-res authored detail",
        "No anatomically verified genital variants, physical contact, calibrated skin/hair/eye shaders",
        "Source MHR geometry units require independent confirmation",
        "All sources generic synthetic adults; no identity reconstruction"]
}
(a.out/"mhr_motion_subdivision_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_MHR_NATIVE_MOTION_SUBDIV",json.dumps({
    "status":receipt["status"],"mode":a.mode,
    "lod0":results["0"],"lod2_vertices":results["2"]["vertices"]
},sort_keys=True))
