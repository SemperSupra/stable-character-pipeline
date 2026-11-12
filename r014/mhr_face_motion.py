"""Technical native MHR LOD1 facial morph motion, not photoreal acting."""
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument("--output",required=True,type=Path)
p.add_argument("--receipt",required=True,type=Path)
args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
args.output.mkdir(parents=True,exist_ok=True)
body=bpy.data.objects["R014_MHR_neutral_body"]
keys=body.data.shape_keys.key_blocks
# Official Meta MHR shape ordering: 45 identity shapes, then 72 facial coefficients.
controls={
    "eyeBlinkLeft":("shape_57",12),
    "eyeBlinkRight":("shape_58",13),
    "jawDrop":("shape_69",24),
    "lipCornerPullerLeft":("shape_77",32),
    "lipCornerPullerRight":("shape_78",33)
}
assert len(keys)==118,("unexpected Basis+117 MHR shape keys",len(keys))
for name,(shape,index) in controls.items():
    assert shape in keys,(name,shape)
    assert shape=="shape_"+str(45+index)
scene=bpy.context.scene
scene.frame_start=1
scene.frame_end=24
scene.render.engine="CYCLES"
scene.cycles.samples=8
scene.cycles.device="CPU"
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.render.resolution_x=320
scene.render.resolution_y=320
scene.render.resolution_percentage=100
world=bpy.data.worlds.new("R014NeutralPortrait")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(.7,.72,.77,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.7
scene.world=world
camdat=bpy.data.cameras.new("R014FacialCamera")
cam=bpy.data.objects.new("R014FacialCamera",camdat)
bpy.context.collection.objects.link(cam)
scene.camera=cam
camdat.type="ORTHO"
camdat.ortho_scale=.54
cam.location=(0,-2.25,1.55)
cam.rotation_euler=(Vector((0,0,1.51))-cam.location).to_track_quat("-Z","Y").to_euler()
ld=bpy.data.lights.new("R014FaceKey","AREA")
lamp=bpy.data.objects.new("R014FaceKey",ld)
bpy.context.collection.objects.link(lamp)
lamp.location=(1.0,-1.6,2.1);ld.energy=240;ld.size=2.0

tracks={
 "shape_57":[(1,0),(8,0),(10,.82),(12,0),(24,0)],
 "shape_58":[(1,0),(8,0),(10,.82),(12,0),(24,0)],
 "shape_69":[(1,0),(6,.55),(12,.25),(18,.65),(24,0)],
 "shape_77":[(1,0),(7,.1),(13,.6),(18,.5),(24,0)],
 "shape_78":[(1,0),(7,.1),(13,.6),(18,.5),(24,0)]
}
for shape,seq in tracks.items():
    sk=keys[shape]
    for frame,value in seq:
        sk.value=value
        sk.keyframe_insert(data_path="value",frame=frame)

dep=bpy.context.evaluated_depsgraph_get()
def snapshot():
    ob=body.evaluated_get(dep)
    me=ob.to_mesh()
    try:
        return [tuple(v.co) for v in me.vertices]
    finally:
        ob.to_mesh_clear()
scene.frame_set(1);base=snapshot()
deltas={}
for frame in (6,10,13,18,24):
    scene.frame_set(frame)
    pts=snapshot()
    deltas[str(frame)]=max((Vector(p)-Vector(q)).length for p,q in zip(pts,base))
assert deltas["6"]>1e-5 and deltas["10"]>1e-5 and deltas["13"]>1e-5
assert deltas["24"]<1e-5,("nonreturning neutral",deltas["24"])
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(args.output/"R014_MHR_face_motion.blend"))
scene.render.image_settings.file_format="FFMPEG"
scene.render.ffmpeg.format="MPEG4"
scene.render.ffmpeg.codec="H264"
scene.render.filepath=str(args.output/"R014_MHR_face_morph_technical.mp4")
bpy.ops.render.render(animation=True)
assert (args.output/"R014_MHR_face_morph_technical.mp4").is_file()

# Export morph-weight animation for an additional portable contract test.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(args.output/"R014_MHR_face_motion.glb"),
                          export_format="GLB",export_morph=True,export_skins=True,
                          export_animations=True,export_yup=True)
report={
 "status":"PASS_MHR_NATIVE_FACIAL_MORPH_MOTION_STRUCTURAL_ONLY",
 "blender":bpy.app.version_string,"frames":24,"fps":scene.render.fps,
 "control_channels":list(controls),"max_local_vertex_delta_by_frame":deltas,
 "video":"R014_MHR_face_morph_technical.mp4",
 "native_blend":"R014_MHR_face_motion.blend","portable_glb":"R014_MHR_face_motion.glb",
 "limits":["No calibrated viseme/audio lip sync","No facial anatomical/acting realism acceptance",
           "No photoreal skin, eyes, teeth or hair",
           "MHR nonlinear neural pose correctives are not transferred"]
}
args.receipt.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print("R014_MHR_FACE_MOTION",json.dumps(report,sort_keys=True))
