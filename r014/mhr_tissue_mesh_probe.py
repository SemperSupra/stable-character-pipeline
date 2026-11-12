"""MHR neutral mesh localized deform-and-bake experiment.

Uses the real licensed MHR LOD1 skin mesh. An uncalibrated spring controller
drives positive/negative morphs on two independently defined *research masks*.
This is NOT anatomically validated soft tissue, collision, internal organ motion,
or photoreal video.
"""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
from r014.tissue_dynamics import RegionParameters,simulate,to_morph_amplitude

p=argparse.ArgumentParser()
p.add_argument("--output",type=Path,required=True)
p.add_argument("--receipt",type=Path,required=True)
args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
args.output.mkdir(parents=True,exist_ok=True)

body=bpy.data.objects["R014_MHR_neutral_body"]
assert body.type=="MESH" and body.data.shape_keys
keys=body.data.shape_keys.key_blocks
assert len(keys)==118,("expected Basis + 45 identity + 72 face shapes",len(keys))
assert all(abs(k.value)<1e-8 for k in list(keys)[1:]),"not a neutral source pose"
basis=keys["Basis"]
inv_vector=body.matrix_world.inverted().to_3x3()

REGIONS=(
    {"region":"left_cheek_research_mask","anchor":(-.075,-.10,1.51),
     "std":(.055,.055,.055),"outward":(0,-1,0),"max_m":.008,
     "params":RegionParameters(.2,180.,18.,.008)},
    {"region":"abdomen_research_mask","anchor":(0,-.075,.97),
     "std":(.13,.09,.12),"outward":(0,-1,0),"max_m":.02,
     "params":RegionParameters(1.2,140.,28.,.02)},
)
scene=bpy.context.scene
scene.frame_start=1;scene.frame_end=48
scene.render.fps=24
measured=[]
traces={}
for region in REGIONS:
    name=region["region"]
    forward=body.shape_key_add(name="R014_"+name+"_positive",from_mix=False)
    reverse=body.shape_key_add(name="R014_"+name+"_negative",from_mix=False)
    count=0
    for i,vert in enumerate(body.data.vertices):
        loc=body.matrix_world@basis.data[i].co
        scalar=sum(((loc[k]-region["anchor"][k])/region["std"][k])**2 for k in range(3))
        weight=math.exp(-.5*scalar)
        if weight<.15:continue
        count+=1
        w=region["max_m"]*weight
        delta=inv_vector@Vector(tuple(x*w for x in region["outward"]))
        forward.data[i].co=basis.data[i].co+delta
        reverse.data[i].co=basis.data[i].co-delta
    assert 40<count<9000,("wrong anatomical mask mapping",name,count)
    def inertial_input(t):
        return 6. if .20<=t<.32 else 0.
    trace=simulate(region["params"],48,24,inertial_input,sample_hz=240)
    traces[name]=trace
    maximum=max(abs(item[0]) for item in trace)
    assert maximum>.0001 and maximum<=region["max_m"]+1e-9,(name,maximum)
    assert abs(trace[-1][0])<.001,("spring did not settle",name,trace[-1])
    for frame,(disp,vel) in enumerate(trace,1):
        morph=to_morph_amplitude(disp,region["max_m"])
        forward.value=morph["positive"]
        reverse.value=morph["negative"]
        forward.keyframe_insert(data_path="value",frame=frame)
        reverse.keyframe_insert(data_path="value",frame=frame)
    measured.append({"region":name,"research_mask_vertices":count,
                     "maximum_dynamic_displacement_m":maximum,
                     "final_displacement_m":trace[-1][0],
                     "illustrative_material":dict(mass=region["params"].mass,
                         stiffness=region["params"].stiffness,damping=region["params"].damping)})

dep=bpy.context.evaluated_depsgraph_get()
def snapshot():
    evaluated=body.evaluated_get(dep)
    mesh=evaluated.to_mesh()
    try:return [tuple(evaluated.matrix_world@v.co) for v in mesh.vertices]
    finally:evaluated.to_mesh_clear()
scene.frame_set(1);base=snapshot()
peak={}
for frame in (7,10,12,20,48):
    scene.frame_set(frame)
    points=snapshot()
    peak[str(frame)]=max((Vector(x)-Vector(y)).length for x,y in zip(points,base))
assert max(peak.values())>.0005,("morph animation not deforming actual mesh",peak)
assert peak["48"]<.001,("non-settling visual rest displacement",peak["48"])

scene.frame_set(1)
blend=args.output/"R014_MHR_local_tissue_morph_research.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
glb=args.output/"R014_MHR_local_tissue_morph_research.glb"
bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",
                          export_morph=True,export_skins=True,
                          export_animations=True,export_yup=True)
assert glb.stat().st_size>100_000

scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=4
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.render.resolution_x=320
scene.render.resolution_y=320
scene.render.resolution_percentage=100
scene.frame_end=24
world=bpy.data.worlds.new("R014TissueWorld")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.7
scene.world=world
lamp_data=bpy.data.lights.new("R014TissueKey","AREA")
lamp=bpy.data.objects.new("R014TissueKey",lamp_data)
bpy.context.collection.objects.link(lamp)
lamp.location=(1,-2,3);lamp_data.energy=420;lamp_data.size=3
cam_data=bpy.data.cameras.new("R014TissueCam")
cam=bpy.data.objects.new("R014TissueCam",cam_data)
bpy.context.collection.objects.link(cam);scene.camera=cam
cam_data.type="ORTHO";cam_data.ortho_scale=.78
cam.location=(0,-2.3,1.4)
cam.rotation_euler=(Vector((0,0,1.4))-cam.location).to_track_quat("-Z","Y").to_euler()
scene.render.filepath=str(args.output/"R014_MHR_tissue_mesh_technical.mp4")
scene.render.image_settings.file_format="FFMPEG"
scene.render.ffmpeg.format="MPEG4"
scene.render.ffmpeg.codec="H264"
bpy.ops.render.render(animation=True)
video=Path(scene.render.filepath)
assert video.stat().st_size>1000
receipt={
  "status":"PASS_ANIMATED_REAL_MESH_ATTACHMENT_STRUCTURAL_ONLY",
  "source_asset":"Meta MHR official LOD1 (see pinned source rights DLE)",
  "source_mesh_vertices":len(body.data.vertices),"shape_keys_total":len(body.data.shape_keys.key_blocks),
  "regions":measured,"evaluated_surface_displacement_m_by_frame":peak,
  "frames":24,"fps":24,"movie_seconds":1.0,"render":"CPU Cycles 320px technical",
  "blend":blend.name,"glb":glb.name,"mp4":video.name,
  "limitations":["Control parameters are not anatomical material measurements",
    "Mask geometry is Gaussian in world-coordinate space, not skin layers",
    "No collisions, contact, local volume conservation or organ solver",
    "No photoreal hair/skin/face or clinical anatomical accuracy",
    "Exported morphs must be qualified independently on destination tools"]
}
args.receipt.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_MHR_TISSUE_MESH",json.dumps(receipt,sort_keys=True))
