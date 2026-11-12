"""Independent fresh-process verification of MPFB CC0 lookdev scene."""
import argparse,json,sys
from pathlib import Path
import bpy
p=argparse.ArgumentParser()
p.add_argument("--blend",required=True,type=Path)
p.add_argument("--receipt",required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.blend.resolve(),"saved scene not reopened"
meshes=[o for o in bpy.data.objects if o.type=="MESH"]
assert len(meshes)>=14,("expected 2 bodies and at least 12 additional meshes",len(meshes))
checks=[]
for sex in ("female","male"):
    body=bpy.data.objects["R014_"+sex+"_textured_body"]
    rig=bpy.data.objects["R014_"+sex+"_textured_rig"]
    assert body.active_material is not None,("missing body skin",sex)
    assert len(rig.data.bones)>20
    assert any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers)
    checks.append({"sex":sex,"body_vertices":len(body.data.vertices),
                   "body_skin_material":body.active_material.name,
                   "bones":len(rig.data.bones)})
images=[im for im in bpy.data.images if im.source=="FILE"]
unpacked=[im.name for im in images if im.packed_file is None]
assert not unpacked,("external missing textures at runtime",unpacked)
result={"status":"PASS_FRESH_REOPEN_MATERIAL_ASSET_REFERENCE_ONLY",
        "bodies":checks,"mesh_objects":len(meshes),"packed_source_images":len(images),
        "limits":["No geometric realism, face animation, organ topology or soft tissue physics acceptance",
                  "No skin/eye/hair visual appearance acceptance"]}
a.receipt.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("R014_MPFB_SURFACE_VERIFY",json.dumps(result,sort_keys=True))
