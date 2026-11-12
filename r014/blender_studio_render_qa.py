"""Neutral orthographic clay views of pinned CC0 realistic sculpt bases.

No eyes/skin/hair materials, rigging, sex-organ topology, realism claims.
"""
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

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

# Explicitly reject factory-startup cube or any unqualified helper geometry.
assert all(o.type!="MESH" or o.name.lower().startswith("geo-body_")
           for o in bpy.data.objects), "Unexpected mesh (factory cube or helper)"
# The upstream asset-library meshes can be stored at arbitrary world offsets.
# Align by each body's actual WORLD bounding box rather than blindly moving
# object origins by a fixed delta.
bpy.context.view_layer.update()
bounds={}
for sex,body in bodies.items():
    verts=[body.matrix_world@Vector(corner) for corner in body.bound_box]
    centroid=Vector((sum(v.x for v in verts)/8,
                     sum(v.y for v in verts)/8,
                     0.))
    target=(-.75,.45) if sex=="female" else (.75,-.45)
    shift=Vector((target[0]-centroid.x,target[1]-centroid.y,
                  -min(v.z for v in verts)))
    relatives=[o for o in bpy.data.objects if
               o.name.lower().startswith("geo-body_"+sex+"_realistic")]
    for obj in relatives:
        if obj.parent is None or obj.parent not in relatives:
            obj.location+=shift
    bpy.context.view_layer.update()
    new_verts=[body.matrix_world@Vector(corner) for corner in body.bound_box]
    bounds[sex]={"min":[min(v[i] for v in new_verts) for i in range(3)],
                 "max":[max(v[i] for v in new_verts) for i in range(3)],
                 "members":[o.name for o in relatives]}

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
scene.camera=camera;camera_data.type="ORTHO";camera_data.ortho_scale=2.8
views=(
 ("pair_front",(0,-6,1.45),(0,0,.92)),
 ("pair_back",(0,6,1.45),(0,0,.92)),
 ("pair_side",(6,0,1.45),(0,0,.92)),
)
for name,pos,target in views:
    camera.location=pos
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
    # Fail closed when a model would be clipped or substantially off-screen.
    for sex,body in bodies.items():
        frame=[world_to_camera_view(scene,camera,body.matrix_world@Vector(pt))
               for pt in body.bound_box]
        xvals=[p.x for p in frame];yvals=[p.y for p in frame]
        if min(xvals)<.015 or max(xvals)>.985 or min(yvals)<.015 or max(yvals)>.985:
            raise ValueError("Body clipped in "+name+": "+sex+" x="+str((min(xvals),max(xvals)))+
                             " y="+str((min(yvals),max(yvals))))
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
 "measured_world_bounds":bounds,
 "camera_coverage_test":"PASS_NO_BODY_CROPPING",
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
