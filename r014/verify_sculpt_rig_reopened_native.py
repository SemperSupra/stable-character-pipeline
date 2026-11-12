"""Independent fresh-process Blender source-vs-sculpt world-coordinate integrity.

The earlier PR #425 scene persisted a stale transform that hid actual registration
errors. A successful save/open operation MUST retain world-space source
correspondence to <10mm p95 reproducibility, otherwise fail CI.
This is not an anatomy, weights, deformation, or video-realism acceptance.
"""
import argparse,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

p=argparse.ArgumentParser()
p.add_argument("--blend",required=True,type=Path)
p.add_argument("--receipt",required=True,type=Path)
p.add_argument("--out",required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.blend.resolve(),"not a fresh opened source scene"
r=json.loads(a.receipt.read_text())
sex=r["sex_source_macro"]
assert sex in (0.,1.)
sname="female" if sex==0 else "male"
src=bpy.data.objects["R014_"+sname+"_body_clean_export"]
sculpt=bpy.data.objects["GEO-body_"+sname+"_realistic"]
assert len(src.data.vertices)==13380
assert len(sculpt.data.vertices)==10582
assert any(m.type=="ARMATURE" for m in sculpt.modifiers)
assert len([m for m in src.modifiers if m.type=="ARMATURE"])==1
bpy.context.view_layer.update()
mat=sculpt.matrix_world
offset=float(np.linalg.norm(np.array(list(mat.translation))))
src_pts=[src.matrix_world@v.co for v in src.data.vertices]
target_pts=[sculpt.matrix_world@v.co for v in sculpt.data.vertices]
src.data.calc_loop_triangles()
faces=[list(t.vertices) for t in src.data.loop_triangles]
bvh=BVHTree.FromPolygons(src_pts,faces,all_triangles=True)
d=[]
for p in target_pts:
    co,_,_,dist=bvh.find_nearest(p)
    assert co is not None
    d.append(dist)
p95=float(np.percentile(d,95))
p50=float(np.percentile(d,50))
initial=r["correspondence"]["p95_m"]
error=abs(p95-initial)
result={
 "sex":sname,
 "status":"PASS_SAVED_NATIVE_SOURCE_GEOMETRY_PARITY_ONLY" if offset<1e-5 and error<.01 else "REJECT_SAVED_NATIVE_TRANSFORM_DRIFT",
 "fresh_reopened":str(a.blend.name),
 "target_object_matrix_translation":list(mat.translation),
 "target_matrix_world_translation_norm":offset,
 "original_pre_save_p95_m":initial,
 "fresh_reopened_p95_m":p95,
 "fresh_reopened_p50_m":p50,
 "p95_reproduction_delta_m":error,
 "source_mesh_vertices":len(src_pts),
 "target_sculpt_vertices":len(target_pts),
 "source_triangles":len(faces),
 "required_anatomical_registration":"HOLD",
 "required_visual_acceptance":"HOLD",
 "limits":["No regional body correspondence gate; cannot claim safe shoulder/hip movement",
           "No FACS expressions, hand contact, local tissue, external reproductive anatomy or photoreal video",
           "Blender Studio Multires not yet enabled for actual posed animation"]
}
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("R014_FRESH_NATIVE_REOPEN_GATE",json.dumps(result,sort_keys=True),flush=True)
if result["status"]!="PASS_SAVED_NATIVE_SOURCE_GEOMETRY_PARITY_ONLY":
    raise SystemExit("Saved Blender scene world-space geometry differs from pre-save measurements")
