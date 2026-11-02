#!/usr/bin/env python3
"""Blender-native authored synthetic hierarchy and multiweight skin, NOT human gait."""
import bpy,json,sys,math,hashlib,pathlib
from mathutils import Vector
a=sys.argv[sys.argv.index("--")+1:]
src=pathlib.Path(a[0]); out=pathlib.Path(a[1]); raw=src.read_bytes(); spec=json.loads(raw)
assert spec["source_class"]=="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
assert spec["private_R009"]=="HELD_NOT_ACCEPTED" and len(spec["frames"])==72
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
receipts={}
for actor,x in zip(spec["actor_ids"],[-0.7,0.7]):
    ad=bpy.data.armatures.new(actor+"_rig"); arm=bpy.data.objects.new(actor,ad)
    scene.collection.objects.link(arm); bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active=arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    hi=ad.edit_bones.new("thigh"); hi.head=(x,0,1.1); hi.tail=(x,0,.6)
    lo=ad.edit_bones.new("shin"); lo.head=hi.tail; lo.tail=(x,0,.12)
    lo.parent=hi;lo.use_connect=True
    foot=ad.edit_bones.new("foot"); foot.head=lo.tail;foot.tail=(x,.2,.12)
    foot.parent=lo;foot.use_connect=True
    bpy.ops.object.mode_set(mode="OBJECT");arm.select_set(False)
    assert ad.bones["shin"].parent==ad.bones["thigh"]
    assert ad.bones["foot"].parent==ad.bones["shin"]
    mesh=bpy.data.meshes.new(actor+"_skin")
    mesh.from_pydata([(x-.05,0,.89),(x+.05,0,.89),(x-.07,0,.6),
        (x+.07,0,.6),(x-.05,0,.36),(x+.05,0,.36)],
        [],[(0,1,3,2),(2,3,5,4)])
    ob=bpy.data.objects.new(actor+"_blended",mesh);scene.collection.objects.link(ob)
    g1=ob.vertex_groups.new(name="thigh");g2=ob.vertex_groups.new(name="shin")
    g1.add([0,1],1.0,"REPLACE");g2.add([4,5],1.0,"REPLACE")
    g1.add([2,3],.5,"REPLACE");g2.add([2,3],.5,"REPLACE")
    m=ob.modifiers.new("RealArmature","ARMATURE");m.object=arm
    for pb in arm.pose.bones:pb.rotation_mode="XYZ"
    for frame in spec["frames"]:
        f=frame["frame"]; arm.pose.bones["thigh"].rotation_euler=(math.radians(frame["hip_deg"]),0,0)
        arm.pose.bones["shin"].rotation_euler=(math.radians(frame["knee_deg"]),0,0)
        for bn in ["thigh","shin"]:arm.pose.bones[bn].keyframe_insert(data_path="rotation_euler",frame=f)
    for i,v in enumerate(mesh.vertices):
        w=[g.weight for g in v.groups];assert abs(sum(w)-1)<1e-6
        if i in [2,3]:assert len(w)==2 and all(.1<t<.9 for t in w)
    def sample(f):
        scene.frame_set(f);bpy.context.view_layer.update()
        ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
        try:return [tuple(ev.matrix_world@v.co) for v in em.vertices]
        finally:ev.to_mesh_clear()
    p0=sample(0);p6=sample(6);p0again=sample(0)
    delta=max(math.dist(x,y) for x,y in zip(p0,p6))
    rewind=max(math.dist(x,y) for x,y in zip(p0,p0again))
    assert delta>.015 and rewind<1e-6
    receipts[actor]={"connected_parent_edges":2,"dual_influence_vertices":2,
        "actual_deformed_mesh_delta_m":delta,"rewind_error_m":rewind}
result={"schema":"scp.r009.public-hierarchical-skin-native.v1",
"status":"PASS_SYNTHETIC_BLENDER_HIERARCHY_AND_MULTIWEIGHT_ONLY",
"source_sha256":hashlib.sha256(raw).hexdigest(),"blender":bpy.app.version_string,
"actors":receipts,"human_rom":"UNKNOWN","human_contact":"UNKNOWN",
"rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC","private_R009":"HELD_NOT_ACCEPTED"}
with out.open("x") as f:json.dump(result,f,indent=2,sort_keys=True);f.write("\n")
print(json.dumps(result))
