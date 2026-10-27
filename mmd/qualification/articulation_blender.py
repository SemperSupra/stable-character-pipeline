#!/usr/bin/env python3
"""Articulation G7 through genuine MMD Blender import + evaluated skin, no proxies."""
import argparse
import json
import math
import os
from pathlib import Path
import sys

def main():
    ap=argparse.ArgumentParser()
    for field in ("source","model","motion","out"):
        ap.add_argument("--"+field,required=True,type=Path)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    import bpy
    from mathutils import Vector
    assert bpy.app.version >= (4,2,0)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sys.path.insert(0,str(a.source.resolve()))
    import mmd_tools
    mmd_tools.register()
    result=bpy.ops.mmd_tools.import_model(filepath=str(a.model.resolve()),
        types={"MESH","ARMATURE"},scale=1.0,
        rename_bones=False,fix_bone_order=False)
    assert "FINISHED" in result,result
    arms=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    meshes=[o for o in bpy.data.objects if o.type=="MESH"]
    assert len(arms)==1 and len(meshes)==1,(arms,meshes)
    rig=arms[0]
    mesh=meshes[0]
    names=("センター","左腕","左手首")
    for name in names:
        assert rig.pose.bones.get(name) is not None, "missing bone "+name
    assert len(mesh.data.vertices)==8 and len(rig.data.bones)==3
    assert len(mesh.vertex_groups)>=3, "lost PMX skin weights"
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    imported=bpy.ops.mmd_tools.import_vmd(
        filepath=str(a.motion.resolve()),
        scale=1.0,margin=0,bone_mapper="PMX",update_scene_settings=False)
    assert "FINISHED" in imported,imported
    scene=bpy.context.scene
    scene.frame_start=0
    scene.frame_end=30
    scene.render.fps=30
    samples={}
    # Compare evaluated mesh vertices in world coordinates, not bones alone.
    rest=[(mesh.matrix_world @ v.co).copy() for v in mesh.data.vertices]
    min_z=min(p.z for p in rest)
    max_z=max(p.z for p in rest)
    anchors=[i for i,p in enumerate(rest) if abs(p.z-min_z)<0.1]
    tips=[i for i,p in enumerate(rest) if abs(p.z-max_z)<0.1]
    assert len(anchors)>=2 and len(tips)>=2,(anchors,tips,[tuple(p) for p in rest])
    for frame in (0,15,30):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        dep=bpy.context.evaluated_depsgraph_get()
        evaluated=mesh.evaluated_get(dep)
        tmp=evaluated.to_mesh()
        try:
            points=[tuple(float(z) for z in (evaluated.matrix_world@v.co)) for v in tmp.vertices]
        finally:
            evaluated.to_mesh_clear()
        rotations={n:tuple(float(v) for v in rig.pose.bones[n].matrix.to_quaternion()) for n in names}
        samples[str(frame)]={"vertices":points,"quaternions_wxyz":rotations}
    initial=samples["0"]["vertices"]
    last=samples["30"]["vertices"]
    motion_amount=[math.dist(a,b) for a,b in zip(initial,last)]
    anchor_max=max(motion_amount[i] for i in anchors)
    tip_min=min(motion_amount[i] for i in tips)
    assert anchor_max<.08, f"root anchor slid too much: {anchor_max}"
    assert tip_min>.12, f"weighted wrist did not deform actual skin: {tip_min}"
    rot_angles={}
    for n in names[1:]:
        q0=samples["0"]["quaternions_wxyz"][n]
        q1=samples["30"]["quaternions_wxyz"][n]
        dot=abs(sum(x*y for x,y in zip(q0,q1)))
        rot_angles[n]=2*math.acos(max(-1.0,min(1.0,dot)))
        assert rot_angles[n]>.12, f"rotating imported MMD VMD joint {n} did not articulate"
    native=a.out/"articulated_ribbon.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(native.resolve()))
    glb=a.out/"articulated_ribbon.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb.resolve()),export_format="GLB",
        export_animations=True,export_skins=True,export_force_sampling=True,
        export_anim_slide_to_zero=True)
    assert native.stat().st_size>1000 and glb.stat().st_size>1000

    # Deliberate diagnostic rendering only AFTER native GLB export:
    # original MMD toon settings are not asserted visually faithful.
    for c in bpy.data.collections:
        c.hide_render=False
        c.hide_viewport=False
    for obj in bpy.data.objects:
        obj.hide_render=False
        obj.hide_viewport=False
    mat=bpy.data.materials.new("G7_EMISSION_ONLY_NOT_MMD_TOON")
    mat.use_nodes=True
    nd=mat.node_tree.nodes
    nd.clear()
    out=nd.new("ShaderNodeOutputMaterial")
    em=nd.new("ShaderNodeEmission")
    em.inputs["Color"].default_value=(0.10,0.92,0.35,1.0)
    em.inputs["Strength"].default_value=2.5
    mat.node_tree.links.new(em.outputs["Emission"],out.inputs["Surface"])
    mesh.data.materials.clear()
    mesh.data.materials.append(mat)
    scene.view_settings.view_transform="Standard"
    cd=bpy.data.cameras.new("G7 Camera")
    cd.type="ORTHO"
    cd.ortho_scale=4.7
    camera=bpy.data.objects.new("G7 Camera",cd)
    scene.collection.objects.link(camera)
    camera.location=(4.0,-5.0,3.6)
    aim=Vector((0.0,0.0,1.5))
    camera.rotation_euler=(aim-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.camera=camera
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=2
    scene.render.resolution_x=360
    scene.render.resolution_y=360
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    for frame in (0,15,30):
        scene.frame_set(frame)
        output=a.out/f"articulation_{frame:04d}.png"
        scene.render.filepath=str(output.resolve())
        bpy.ops.render.render(write_still=True)
        assert output.stat().st_size>1000
    receipt={
       "schema":"scp.mmd.articulation.blender.v1",
       "status":"PASS_IMPORTED_MULTI_BONE_WEIGHTED_SKIN_AND_TWO_JOINT_ROTATIONS",
       "blender":bpy.app.version_string,
       "mmd_tools":mmd_tools.MMD_TOOLS_VERSION,
       "rig_bone_names":list(names),
       "vertex_count":len(rest),
       "anchor_vertex_indices":anchors,
       "tip_vertex_indices":tips,
       "anchor_max_motion":anchor_max,
       "tip_min_motion":tip_min,
       "joint_angles_radians":rot_angles,
       "samples":samples,
       "glb":glb.name,
       "editable_blend":native.name,
       "render_shader":"diagnostic emission, NOT MMD toon fidelity",
       "unqualified":["MMD native IK","rigidbody physics","retargeted humanoid anatomy","hair/cloth/soft tissue","third-party model rights"]
    }
    (a.out/"articulation_blender_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
