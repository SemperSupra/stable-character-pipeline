"""Independent fresh-process MHR localized-morph persistence and motion check."""
import argparse,json,struct,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument("--blend",required=True,type=Path)
p.add_argument("--glb",required=True,type=Path)
p.add_argument("--receipt",required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.blend.resolve()
body=bpy.data.objects["R014_MHR_neutral_body"]
keys=body.data.shape_keys.key_blocks
names=["R014_left_cheek_research_mask_positive",
       "R014_left_cheek_research_mask_negative",
       "R014_abdomen_research_mask_positive",
       "R014_abdomen_research_mask_negative"]
assert len(keys)==122
assert all(name in keys for name in names)
dg=bpy.context.evaluated_depsgraph_get()
def snapshot():
    ev=body.evaluated_get(dg)
    m=ev.to_mesh()
    try:return [tuple(ev.matrix_world@v.co) for v in m.vertices]
    finally:ev.to_mesh_clear()
bpy.context.scene.frame_set(1)
base=snapshot()
bpy.context.scene.frame_set(12)
posed=snapshot()
assert len(base)==len(posed)>10000
delta=max((Vector(x)-Vector(y)).length for x,y in zip(base,posed))
assert delta>.0005,("reopened real skin does not deform",delta)
bpy.context.scene.frame_set(48)
settled=snapshot()
rest=max((Vector(x)-Vector(y)).length for x,y in zip(base,settled))
assert rest<.001,("not settled",rest)
with a.glb.open("rb") as f:
    h=f.read(12);magic,version,length=struct.unpack("<4sII",h)
    assert magic==b"glTF" and version==2 and length==a.glb.stat().st_size
    num,kind=struct.unpack("<I4s",f.read(8))
    assert kind==b"JSON"
    g=json.loads(f.read(num))
assert any(ch.get("target",{}).get("path")=="weights"
           for anim in g.get("animations",[]) for ch in anim.get("channels",[])), \
       "morph animation not exported to GLB"
result={"status":"PASS_NATIVE_REHYDRATION_MORPH_AND_GLTF_CONTRACT_ONLY",
        "reopened_deformation_m":delta,"reopened_settled_delta_m":rest,
        "morph_names":names,"glb_animations":len(g["animations"]),
        "limits":["Not a physical soft-body or organ simulation",
                  "Not a destination GLB rendered deformation parity proof"]}
a.receipt.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("R014_TISSUE_REOPEN",json.dumps(result,sort_keys=True))
