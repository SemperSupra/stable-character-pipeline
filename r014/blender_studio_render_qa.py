"""Neutral orthographic clay views of pinned CC0 realistic sculpt bases.

No eyes/skin/hair materials, rigging, sex-organ topology, realism claims.
"""
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument("--blend",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
p.add_argument("--receipt",type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.blend.resolve(),"base scene not freshly reopened"
a.out.mkdir(parents=True,exist_ok=True)
bodies={}
for sex in ("female","male"):
    body=bpy.data.objects["GEO-body_"+sex+"_realistic"]
    assert body.type=="MESH" and len(body.data.vertices)==10582
    assert any(m.type=="MULTIRES" for m in body.modifiers)
    bodies[sex]=body

# Move source meshes and eye components together into a standard two-model
# survey scene without modifying stored mesh topology or UV mapping.
for obj in bpy.data.objects:
    name=obj.name.lower()
    if "geo-body_female_realistic" in name:shift=-.8
    elif "geo-body_male_realistic" in name:shift=.8
    else:continue
    if obj.parent is None:obj.location.x+=shift

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=12
scene.render.threads_mode="FIXED";scene.render.threads=4
scene.render.resolution_x=768;scene.render.resolution_y=768
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
world=bpy.data.worlds.new("R014SculptNeutralWorld")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(.72,.75,.78,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.85
scene.world=world
area_data=bpy.data.lights.new("R014SculptKey","AREA")
area=bpy.data.objects.new("R014SculptKey",area_data)
bpy.context.collection.objects.link(area)
area.location=(1,-3,4)
area_data.energy=600;area_data.size=5
camera_data=bpy.data.cameras.new("R014SculptSurveyCamera")
camera=bpy.data.objects.new("R014SculptSurveyCamera",camera_data)
bpy.context.collection.objects.link(camera)
scene.camera=camera;camera_data.type="ORTHO";camera_data.ortho_scale=2.5
views=(
 ("pair_front",(0,-6,1.45),(0,0,.92)),
 ("pair_back",(0,6,1.45),(0,0,.92)),
 ("pair_side",(6,0,1.45),(0,0,.92)),
)
for name,pos,target in views:
    camera.location=pos
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(a.out/("sculpt_"+name+".png"))
    bpy.ops.render.render(write_still=True)
    assert Path(scene.render.filepath).stat().st_size>10000
# Retain inspectable Blender scene with camera/lighting; no linked external paths.
native=a.out/"R014_BlenderStudio_realistic_bases_neutral_survey.blend"
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>100_000
result={
 "status":"PASS_NEUTRAL_RENDER_EVIDENCE_CREATED_NOT_ANATOMY_QUALIFIED",
 "source":"Blender Studio Human Base Meshes v1.4.1 CC0 publisher",
 "native_survey_blend":native.name,
 "renders":["sculpt_pair_front.png","sculpt_pair_back.png","sculpt_pair_side.png"],
 "models":[{"sex":sex,"vertices":len(body.data.vertices),
            "faces":len(body.data.polygons),"uv_layers":len(body.data.uv_layers),
            "rig":any(m.type=="ARMATURE" for m in body.modifiers)}
           for sex,body in bodies.items()],
 "limits":["Clay-only survey, not textured photoreal output",
           "No full genital anatomy acceptance, sculpt readiness not sex-organ readiness",
           "No rigged pose, soft-body deformation, contact or video"]
}
a.receipt.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("R014_BLENDER_STUDIO_VISUAL",json.dumps(result,sort_keys=True))
