"""Independent fresh-process source-native CC0 textured morph and rig qualification."""
import argparse,json,math,sys
from pathlib import Path
import bpy

p=argparse.ArgumentParser()
p.add_argument("--source",type=Path,required=True)
p.add_argument("--receipt",type=Path,required=True)
p.add_argument("--sex",choices=["male","female"],required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.source.resolve()
r=json.loads(a.receipt.read_text())
assert r["status"]=="PASS_SOURCE_NATIVE_CC0_MORPH_MOTION_RENDER_STRUCTURAL_ONLY"
assert r["sex_macro_label"]==a.sex
rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
assert len(rig.data.bones)==163 and len(body.data.vertices)==19158
assert body.active_material and body.active_material.use_nodes
assert len([m for m in body.modifiers if m.type=="ARMATURE" and m.object==rig])==1
packed=[im.name for im in bpy.data.images if im.source=="FILE" and im.packed_file]
assert len(packed)>=1
def pts():
  dg=bpy.context.evaluated_depsgraph_get()
  ev=body.evaluated_get(dg);m=ev.to_mesh()
  try:return [tuple(ev.matrix_world@v.co) for v in m.vertices]
  finally:ev.to_mesh_clear()
values=[]
for frame in (1,8,16):
  bpy.context.scene.frame_set(frame)
  bpy.context.view_layer.update()
  values.append(pts())
assert all(len(v)==len(values[0]) for v in values)
motion=max(math.dist(a,b) for a,b in zip(values[0],values[1]))
rest=max(math.dist(a,b) for a,b in zip(values[0],values[2]))
assert motion>1e-4 and rest<1e-4
result={"schema":"r014.cc0.morph.native.reopen.v1",
        "status":"PASS_FRESH_REOPEN_TEXTURED_MORPH_ACTUATED_MESH_ONLY",
        "sex_macro_label":a.sex,"vertices":len(body.data.vertices),
        "bones":len(rig.data.bones),"packed_images":len(packed),
        "posed_max_delta_blender_units":round(motion,7),
        "returned_max_delta_blender_units":round(rest,9),
        "native_photoreal_acceptance":"HOLD",
        "anatomy_completeness":"UNKNOWN",
        "source_packed_materials_verified":True}
a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("R014_CC0_MORPH_REOPEN",json.dumps(result,sort_keys=True))
