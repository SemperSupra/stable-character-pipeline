"""MPFB native-to-GLB matched *animated pose* metric, no realism acceptance."""
import argparse,json,math,struct,sys
from pathlib import Path
import bpy
from mathutils import Vector,kdtree

p=argparse.ArgumentParser()
p.add_argument("--out",type=Path,required=True)
p.add_argument("--receipt",type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)

def mesh_and_rig(sex):
    obj=bpy.data.objects["R014_"+sex+"_body_clean_export"]
    arms=[m.object for m in obj.modifiers if m.type=="ARMATURE" and m.object is not None]
    assert len(arms)==1,("missing unique armature",sex,len(arms))
    return obj,arms[0]

def points(obj):
    dg=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(dg)
    m=ev.to_mesh()
    try:return [tuple(ev.matrix_world@v.co) for v in m.vertices]
    finally:ev.to_mesh_clear()

def nearest_stats(reference,actual):
    tree=kdtree.KDTree(len(reference))
    for i,v in enumerate(reference):tree.insert(Vector(v),i)
    tree.balance()
    distances=sorted(tree.find(Vector(v))[2] for v in actual)
    return {"rms_m":math.sqrt(sum(d*d for d in distances)/len(distances)),
            "p95_m":distances[min(len(distances)-1,int(.95*len(distances)))],
            "max_m":distances[-1]}

sexes=("female","male")
scene=bpy.context.scene
scene.frame_start=1;scene.frame_end=24
for sex in sexes:
    obj,rig=mesh_and_rig(sex)
    for name in ("upperarm01.L","upperleg01.L"):
        assert name in rig.pose.bones,("bone missing",sex,name)
        b=rig.pose.bones[name]
        b.rotation_mode="XYZ"
        for frame,angle in ((1,0.),(12,.35 if name=="upperarm01.L" else -.24),(24,0.)):
            b.rotation_euler[1]=angle
            b.keyframe_insert(data_path="rotation_euler",frame=frame)
scene.frame_set(1)
reference={}
for frame in (1,12):
    scene.frame_set(frame);bpy.context.view_layer.update()
    for sex in sexes:
        body,_=mesh_and_rig(sex)
        reference[(sex,frame)]=points(body)
scene.frame_set(1)

# Export only helper-free rigs and bodies; untouched original art-source is excluded.
bpy.ops.object.select_all(action="DESELECT")
for sex in sexes:
    body,rig=mesh_and_rig(sex)
    body.select_set(True);rig.select_set(True)
bpy.context.view_layer.objects.active=mesh_and_rig("female")[1]
export=a.out/"R014_MPFB_animated_pose_parity.glb"
bpy.ops.export_scene.gltf(filepath=str(export),export_format="GLB",
                          use_selection=True,export_animations=True,
                          export_morph=True,export_skins=True,export_yup=True)

# Check actual GLB animation exists, before Blender reimport could hide an export loss.
with export.open("rb") as f:
    f.read(12);json_size,kind=struct.unpack("<I4s",f.read(8))
    assert kind==b"JSON"
    gltf=json.loads(f.read(json_size))
assert gltf.get("animations"),"missing exported joint animation"
assert any(ch.get("target",{}).get("path")=="rotation"
           for anim in gltf["animations"] for ch in anim.get("channels",[])), \
       "no actual animated joint rotations in portable GLB"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(export))
report={"status":"MEASURED_GLTF_ANIMATED_SKIN_PARITY_UNQUALIFIED",
        "blender":bpy.app.version_string,
        "native_export_target":"GLB animation with Blender glTF maximum four joint influences",
        "animations_in_glb":len(gltf["animations"]),
        "measurements":{},
        "limits":["Nearest neighbor distances mix topology differences and skinning changes",
                  "This is not material/anatomical or rig retarget acceptance",
                  "Tolerance and body-region thresholds require reference calibration",
                  "Neural pose correctives and true tissue physics not tested"]}
for frame in (1,12):
    scene.frame_set(frame);bpy.context.view_layer.update()
    for sex in sexes:
        body,_=mesh_and_rig(sex)
        actual=points(body);orig=reference[(sex,frame)]
        both=nearest_stats(orig,actual)
        opposite=nearest_stats(actual,orig)
        report["measurements"][sex+"_frame_"+str(frame)] = {
            "source_vertices":len(orig),"reimported_vertices":len(actual),
            "actual_to_native":both,"native_to_actual":opposite}
a.receipt.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print("R014_POSE_PARITY",json.dumps(report,sort_keys=True))
