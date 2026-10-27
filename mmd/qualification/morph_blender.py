#!/usr/bin/env python3
"""G9: actual MMD Blender PMX vertex morph and VMD face import and render."""
import argparse
import json
import math
import os
from pathlib import Path
import sys

def main():
    p=argparse.ArgumentParser()
    for n in ("source","model","motion","out"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    import bpy
    from mathutils import Vector
    assert bpy.app.version >= (4,2,0)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sys.path.insert(0,str(a.source.resolve()))
    import mmd_tools
    mmd_tools.register()
    result=bpy.ops.mmd_tools.import_model(filepath=str(a.model.resolve()),
      types={"MESH","ARMATURE","MORPHS"},scale=1.0,
      rename_bones=False,fix_bone_order=False)
    assert "FINISHED" in result,result
    meshes=[o for o in bpy.data.objects if o.type=="MESH" and len(o.data.vertices)==16]
    assert len(meshes)==1,[(o.name,len(o.data.vertices)) for o in bpy.data.objects if o.type=="MESH"]
    mesh=meshes[0]
    assert len(mesh.data.vertices)==16
    assert mesh.data.shape_keys is not None,"upstream PMX import lost morph shape keys"
    keys=mesh.data.shape_keys.key_blocks
    assert "まばたき" in keys and "笑い" in keys,[k.name for k in keys]
    bpy.ops.object.select_all(action="DESELECT")
    # Upstream ImportVmd explicitly says root => armature and morph, mesh => morph;
    # armature-only selection silently skips all VMD morph frames.
    mesh.select_set(True)
    bpy.context.view_layer.objects.active=mesh
    loaded=bpy.ops.mmd_tools.import_vmd(
       filepath=str(a.motion.resolve()),scale=1.0,
       margin=0,bone_mapper="PMX",update_scene_settings=False)
    assert "FINISHED" in loaded,loaded
    scene=bpy.context.scene
    scene.frame_start=0
    scene.frame_end=30
    scene.render.fps=30
    samples={}
    for frame in (0,15,30):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        d=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        em=d.to_mesh()
        try:
            pts=[tuple(float(x) for x in (d.matrix_world@v.co)) for v in em.vertices]
        finally:
            d.to_mesh_clear()
        samples[str(frame)]={
          "weights":{"まばたき":float(keys["まばたき"].value),"笑い":float(keys["笑い"].value)},
          "vertices":pts
        }
    a0,a15,a30=[samples[str(x)] for x in (0,15,30)]
    assert a0["weights"]["まばたき"]<.01
    assert a15["weights"]["まばたき"]>.95
    assert a30["weights"]["まばたき"]<.01
    assert a0["weights"]["笑い"]<.01
    assert .2<a15["weights"]["笑い"]<.5
    assert a30["weights"]["笑い"]>.95
    displacement_blink=max(math.dist(p,q) for p,q in zip(a0["vertices"],a15["vertices"]))
    displacement_smile=max(math.dist(p,q) for p,q in zip(a0["vertices"],a30["vertices"]))
    assert displacement_blink>.1 and displacement_smile>.1,(displacement_blink,displacement_smile)
    blend=a.out/"synthetic_face_morph.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    glb=a.out/"synthetic_face_morph.glb"
    bpy.ops.export_scene.gltf(
      filepath=str(glb.resolve()),export_format="GLB",
      export_animations=True,export_morph=True,export_skins=True,
      export_force_sampling=True,export_anim_slide_to_zero=True)
    assert blend.stat().st_size>1000 and glb.stat().st_size>1000
    # Render clearly labeled actual imported/animated geometry after source GLB export.
    for o in bpy.data.objects:
        o.hide_render=False
        o.hide_viewport=False
    for c in bpy.data.collections:
        c.hide_render=False
        c.hide_viewport=False
    material=bpy.data.materials.new("G9_DIAGNOSTIC_NOT_NATIVE_MMD_TOON")
    material.use_nodes=True
    nodes=material.node_tree.nodes
    nodes.clear()
    output=nodes.new("ShaderNodeOutputMaterial")
    emission=nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value=(0.85,0.48,0.14,1.0)
    emission.inputs["Strength"].default_value=2.0
    material.node_tree.links.new(emission.outputs["Emission"],output.inputs["Surface"])
    mesh.data.materials.clear()
    mesh.data.materials.append(material)
    camera_data=bpy.data.cameras.new("G9")
    camera_data.type="ORTHO"
    camera_data.ortho_scale=5.2
    camera=bpy.data.objects.new("G9",camera_data)
    scene.collection.objects.link(camera)
    camera.location=(0,-5,1.0)
    camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.camera=camera
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=2
    scene.render.resolution_x=300
    scene.render.resolution_y=300
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    for frame in (0,15,30):
        scene.frame_set(frame)
        out=a.out/f"morph_{frame:04d}.png"
        scene.render.filepath=str(out.resolve())
        bpy.ops.render.render(write_still=True)
        assert out.stat().st_size>900,out
    report={
       "schema":"scp.mmd.morph.blender.v1",
       "status":"PASS_NATIVE_PMX_MORPH_AND_VMD_SHAPE_ANIMATION",
       "blender":bpy.app.version_string,
       "upstream_mmd_tools":mmd_tools.MMD_TOOLS_VERSION,
       "source_geometry":"self-authored 4x4 plane",
       "morph_names":["まばたき","笑い"],
       "samples":samples,
       "max_blink_displacement":displacement_blink,
       "max_smile_displacement":displacement_smile,
       "scope":"PMX vertex morph and native VMD shape key source; diagnostic renderer only",
       "unqualified":["human facial realism","natural expression","bone morphs","material morphs","native MMD render parity"]
    }
    (a.out/"morph_blender_receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="samples"}),flush=True)

if __name__=="__main__":
    main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
