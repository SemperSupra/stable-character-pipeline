"""Original synthetic material/camera/animation scene for Blender version comparison."""
import bpy
import json
import os
from pathlib import Path
from math import radians
out = Path(os.environ.get("R095_OUT", "/tmp/r095-render"))
out.mkdir(parents=True, exist_ok=True)
version = ".".join(map(str, bpy.app.version))
expected = os.environ["R095_VERSION"]
assert version == expected, (version, expected)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=(0, 0, 0))
obj=bpy.context.object
obj.name="SyntheticMovingSkin"
mat=bpy.data.materials.new("OriginalSyntheticSurface")
mat.diffuse_color=(0.62,0.24,0.12,1)
mat.use_nodes=True
bsdf=mat.node_tree.nodes.get("Principled BSDF")
assert bsdf
bsdf.inputs["Base Color"].default_value=(0.62,0.24,0.12,1)
bsdf.inputs["Roughness"].default_value=0.58
obj.data.materials.append(mat)
for f,z in ((1,0.0),(12,0.25),(24,0.0)):
    obj.location.z=z
    obj.keyframe_insert(data_path="location",frame=f)
bpy.ops.mesh.primitive_plane_add(size=6,location=(0,0,-1.02))
plane=bpy.context.object
plane.name="SyntheticFloor"
floor=bpy.data.materials.new("GreyFloor")
floor.diffuse_color=(0.44,0.44,0.44,1)
plane.data.materials.append(floor)
camera_data=bpy.data.cameras.new("ParityCamera")
cam=bpy.data.objects.new("ParityCamera",camera_data)
bpy.context.scene.collection.objects.link(cam)
cam.location=(3.0,-5.5,2.0)
target=bpy.mathutils.Vector((0,0,0)) if hasattr(bpy,"mathutils") else None
from mathutils import Vector
cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat("-Z","Y").to_euler()
bpy.context.scene.camera=cam
lamp_data=bpy.data.lights.new("ParityKey","AREA")
lamp=bpy.data.objects.new("ParityKey",lamp_data)
bpy.context.scene.collection.objects.link(lamp)
lamp.location=(1.5,-2,4)
lamp_data.energy=400
lamp_data.shape="DISK"
lamp_data.size=3
bpy.context.scene.render.engine="CYCLES"
bpy.context.scene.cycles.device="CPU"
bpy.context.scene.cycles.samples=8
bpy.context.scene.render.image_settings.file_format="PNG"
bpy.context.scene.render.image_settings.color_mode="RGBA"
bpy.context.scene.render.image_settings.color_depth="8"
bpy.context.scene.render.resolution_x=96
bpy.context.scene.render.resolution_y=96
bpy.context.scene.render.resolution_percentage=100
bpy.context.scene.render.film_transparent=False
bpy.context.scene.render.image_settings.compression=15
bpy.context.scene.view_settings.view_transform="Standard"
bpy.context.scene.view_settings.look="Medium High Contrast" if "Medium High Contrast" in [x.name for x in bpy.types.ColorManagedViewSettings.bl_rna.properties["look"].enum_items] else "Medium High Contrast"
for frame in (1,12,24):
    bpy.context.scene.frame_set(frame)
    bpy.context.scene.render.filepath=str(out/("frame_%04d.png"%frame))
    bpy.ops.render.render(write_still=True)
    assert (out/("frame_%04d.png"%frame)).stat().st_size>100
# Independent diagnostic emission-only rendering isolates light/material shading from color/view/image pipeline.
for material, rgba in ((mat,(0.62,0.24,0.12,1)),(floor,(0.44,0.44,0.44,1))):
    material.use_nodes=True
    nodes=material.node_tree.nodes
    nodes.clear()
    output=nodes.new("ShaderNodeOutputMaterial")
    emit=nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value=rgba
    emit.inputs["Strength"].default_value=1.0
    material.node_tree.links.new(emit.outputs["Emission"],output.inputs["Surface"])
bpy.context.scene.frame_set(12)
bpy.context.scene.render.filepath=str(out/"emission_0012.png")
bpy.ops.render.render(write_still=True)
assert (out/"emission_0012.png").stat().st_size>100
# Controlled diffuse-only path: tests whether the large difference is Principled-specific.
for material, rgba in ((mat,(0.62,0.24,0.12,1)),(floor,(0.44,0.44,0.44,1))):
    nodes=material.node_tree.nodes
    nodes.clear()
    output=nodes.new("ShaderNodeOutputMaterial")
    diffuse=nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.inputs["Color"].default_value=rgba
    diffuse.inputs["Roughness"].default_value=0.0
    material.node_tree.links.new(diffuse.outputs["BSDF"],output.inputs["Surface"])
bpy.context.scene.render.filepath=str(out/"diffuse_0012.png")
bpy.ops.render.render(write_still=True)
assert (out/"diffuse_0012.png").stat().st_size>100
print("R095_RENDER",json.dumps({"version":version,"frames":[1,12,24],"resolution":[96,96],"render":"cycles-cpu-8spp","source":"original-synthetic"}))
