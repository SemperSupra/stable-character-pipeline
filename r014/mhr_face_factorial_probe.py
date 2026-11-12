"""R014: real MHR expression shape isolation with fixed-polygon deformation QA.

Native Blender 4.5 scene only; do not infer FACS validity or photorealism.
No private likeness, no protected media, source weights, or personal photos.
"""
import argparse, json, math, sys
from pathlib import Path
from collections import defaultdict
import bpy
import numpy as np
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument("--out",required=True,type=Path)
p.add_argument("--mode",choices=("single","combination"),required=True)
args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
args.out.mkdir(parents=True,exist_ok=True)
body=bpy.data.objects["R014_MHR_neutral_body"]
rig=bpy.data.objects["R014_MHR_neutral_rig"]
keys=body.data.shape_keys.key_blocks
assert len(keys)==118 and len(rig.data.bones)==126
assert len(body.data.vertices)==18439
assert any(m.type=="ARMATURE" and m.object is rig for m in body.modifiers)
assert Path(bpy.data.filepath).name=="R014_MHR_neutral_lod1.blend"

controls={
    "shape_57":"eyeBlinkLeft_provisional",
    "shape_58":"eyeBlinkRight_provisional",
    "shape_69":"jawDrop_provisional",
    "shape_77":"lipCornerPullerLeft_provisional",
    "shape_78":"lipCornerPullerRight_provisional",
}
for k in controls:
    assert k in keys
    keys[k].slider_min=-1.0
    keys[k].slider_max=1.0
    keys[k].value=0.0

scene=bpy.context.scene
scene.frame_set(1)
bpy.context.view_layer.update()

def geometry():
    dg=bpy.context.evaluated_depsgraph_get()
    ob=body.evaluated_get(dg)
    mesh=ob.to_mesh()
    try:
        vertices=np.array([list(ob.matrix_world@v.co) for v in mesh.vertices],np.float64)
        # Compare per-polygon vertex member order, not Blender's
        # geometry-dependent quad triangulation (previous false topology FAIL).
        polygons=[tuple(int(x) for x in f.vertices) for f in mesh.polygons]
    finally:
        ob.to_mesh_clear()
    if len(vertices)!=18439 or not np.isfinite(vertices).all():
        raise RuntimeError("unexpected/nonfinite evaluated source mesh")
    return vertices,polygons

rest,polygons=geometry()
triangles=np.array([
    (poly[0],poly[j],poly[j+1])
    for poly in polygons for j in range(1,len(poly)-1)
],dtype=np.int32)
assert len(triangles)==36874 and len(polygons)>10000
a,b,c=(rest[triangles[:,j]] for j in range(3))
base_norm=np.cross(b-a,c-a)
base_mag=np.linalg.norm(base_norm,axis=1)
valid=base_mag>1e-11
assert int(np.count_nonzero(~valid))==0,("invalid neutral topology",int(np.count_nonzero(~valid)))
zmin=float(rest[:,2].min());zmax=float(rest[:,2].max())
head_border=zmin+.73*(zmax-zmin)
headfaces=np.mean(rest[triangles,2],axis=1)>=head_border

def evaluate(label,values):
    for name in controls:
        keys[name].value=float(values.get(name,0))
    bpy.context.view_layer.update()
    moved,newpoly=geometry()
    if newpoly!=polygons:
        raise ValueError("MHR evaluated polygon vertex topology actually changed")
    aa,bb,cc=(moved[triangles[:,j]] for j in range(3))
    n=np.cross(bb-aa,cc-aa)
    mag=np.linalg.norm(n,axis=1)
    flip=valid & (np.einsum('ij,ij->i',base_norm,n)<=0)
    collapse=valid & (mag < .10*base_mag)
    shift=np.linalg.norm(moved-rest,axis=1)
    bad=np.flatnonzero(flip|collapse)
    return {
        "case":label,
        "values":dict(values),
        "inversions":int(flip.sum()),
        "inversions_in_head_proxy":int(np.count_nonzero(flip&headfaces)),
        "collapses_below_tenth_area":int(collapse.sum()),
        "moving_vertices_gt_1mm":int(np.count_nonzero(shift>.001)),
        "max_vertex_shift_raw_units":float(shift.max()),
        "p95_vertex_shift_raw_units":float(np.percentile(shift,95)),
        "implicated_faces":[{
          "triangle_index":int(k),
          "vertex_ids":triangles[k].tolist(),
          "rest_centroid_raw":rest[triangles[k]].mean(axis=0).tolist(),
          "area_ratio":float(mag[k]/max(base_mag[k],1e-11)),
          "is_head_proxy":bool(headfaces[k])
        } for k in bad[:80]],
        "count_implicated_faces":int(len(bad))
    }

cases=[]
if args.mode=="single":
    for name in controls:
        for amp in (.15,.30,.50,.70):
            cases.append((name+"_"+str(amp),{name:amp}))
else:
    cases=[
        ("both_eyes_half",{"shape_57":.5,"shape_58":.5}),
        ("jaw_only_mid",{"shape_69":.5}),
        ("mouth_symmetric_mid",{"shape_77":.35,"shape_78":.35}),
        ("blink_jaw_mid",{"shape_57":.5,"shape_58":.5,"shape_69":.5}),
        ("mouth_jaw_mid",{"shape_69":.5,"shape_77":.35,"shape_78":.35}),
        ("all_source_recipe",{"shape_57":.50,"shape_58":.50,"shape_69":.50,"shape_77":.35,"shape_78":.35}),
        ("all_half_recipe",{"shape_57":.25,"shape_58":.25,"shape_69":.25,"shape_77":.175,"shape_78":.175}),
        ("all_quarter_recipe",{"shape_57":.125,"shape_58":.125,"shape_69":.125,"shape_77":.0875,"shape_78":.0875}),
    ]
observations=[evaluate(label,vals) for label,vals in cases]
# Never treat a green capture as a pass on morphology or facial acting.
safe=[x for x in observations if x["inversions"]==0 and x["collapses_below_tenth_area"]==0]
selection=max(safe,key=lambda x:(len(x["values"]),x["moving_vertices_gt_1mm"]),default=None)
if selection is None:
    selection=min(observations,key=lambda x:(x["inversions"]+x["collapses_below_tenth_area"],-x["moving_vertices_gt_1mm"]))
chosen=dict(selection["values"])
for f,mult in ((1,0),(12,1),(24,0)):
    scene.frame_set(f)
    for name in controls:
        k=keys[name]
        k.value=chosen.get(name,0)*mult
        k.keyframe_insert(data_path="value",frame=f)
bpy.context.view_layer.update()

native=args.out/("R014_MHR_face_"+args.mode+"_factorial_HOLD.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>100000

scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=8
scene.render.threads_mode="FIXED";scene.render.threads=4
scene.render.resolution_x=768;scene.render.resolution_y=768
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
world=bpy.data.worlds.new("R014_MHR_Facial_QA_World")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.8
scene.world=world
ld=bpy.data.lights.new("R014FaceKey","AREA")
lamp=bpy.data.objects.new("R014FaceKey",ld)
bpy.context.collection.objects.link(lamp)
lamp.location=(1,-1.5,zmax+.35);ld.energy=350;ld.size=2
camera_data=bpy.data.cameras.new("R014FaceCloseup","PERSP")
camera=bpy.data.objects.new("R014FaceCloseup",camera_data)
bpy.context.collection.objects.link(camera)
scene.camera=camera
camera_data.type="ORTHO";camera_data.ortho_scale=.55
head_z=zmax-.17
camera.location=(0,-2.2,head_z)
camera.rotation_euler=(Vector((0,0,head_z))-camera.location).to_track_quat("-Z","Y").to_euler()
for frame,label in ((1,"neutral"),(12,"expression")):
    scene.frame_set(frame)
    scene.render.filepath=str(args.out/(args.mode+"_"+label+"_face_closeup.png"))
    bpy.ops.render.render(write_still=True)
    if Path(scene.render.filepath).stat().st_size<5000:
        raise RuntimeError("unusable face closeup frame")
receipt={
    "status":"HOLD_FACIAL_ANATOMY_AND_CINEMATIC_QUALITY",
    "source":"official pinned MHR v1.0.1 Blender imported LOD1",
    "source_release_sha256":"e4f4f205cd87c0fa106577ba1de4fc763e4eb197c924461d2ef7e6944e9d6b94",
    "mode":args.mode,
    "mesh_vertices":len(rest),
    "source_rig_bones":len(rig.data.bones),
    "triangulation":"fixed polygon vertex fan; stable across morph poses, differs from Blender dynamic quad diagonals",
    "head_region":"proxy based on top 27% of rest vertical bounds; NOT validated anatomy landmark",
    "control_semantics":controls,
    "case_count":len(observations),
    "cases":observations,
    "selected_visual_case":selection["case"],
    "selected_case_is_zero_foldover_sample_only":selection in safe,
    "native_blend":native.name,
    "closeup_pngs":[args.mode+"_neutral_face_closeup.png",args.mode+"_expression_face_closeup.png"],
    "limitations":[
        "Positive research capture does not accept anatomical/acting quality or photorealism",
        "Five provisional morph labels not FACS clinically validated",
        "Source facial topology may fold under realistic expression combinations",
        "No eye-corneal materials, dental/tongue rig validation, lip seal or speech",
        "No MHR nonlinear neural pose corrective export verified",
        "This does not verify source full-body sex/anatomy, body variations or physics"
    ]
}
(args.out/"mhr_face_factorial_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_FACE_FACTORIAL",json.dumps({"status":receipt["status"],"mode":args.mode,
    "cases":len(observations),"inversion_min":min(x["inversions"] for x in observations),
    "inversion_max":max(x["inversions"] for x in observations),
    "selected":selection["case"],"selected_zero_foldover":selection in safe},sort_keys=True))
