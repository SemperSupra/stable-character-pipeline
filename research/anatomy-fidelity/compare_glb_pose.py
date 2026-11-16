"""R036: independently reimport MPFB official glTF exports and measure posed geometry.

Source: inherited pinned native MPFB probe (draft parent PR #525). No actual
anatomical truth or photorealism claims. The tolerance is only a deliberately
large smoke bound; all numerical evidence remains available for review.
"""
import bpy
import argparse
import hashlib
import json
import math
import os
import sys
from mathutils import kdtree

def parse():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    return p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])

def fail(msg):
    print("R036_GLTF_REIMPORT_FAIL",msg)
    raise RuntimeError(msg)

def points(obj):
    bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get()
    evaluated=obj.evaluated_get(graph)
    mesh=evaluated.to_mesh()
    try:
        return [evaluated.matrix_world@v.co for v in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()

def nearest_distances(a,b):
    if not a or not b:fail("empty point cloud")
    tree=kdtree.KDTree(len(b))
    for i,p in enumerate(b):tree.insert(p,i)
    tree.balance()
    ds=sorted(tree.find(p)[2] for p in a)
    n=len(ds)
    return {"n":n,"mean_m":sum(ds)/n,"p95_m":ds[min(n-1,math.ceil(.95*n)-1)],
      "p99_m":ds[min(n-1,math.ceil(.99*n)-1)],"max_m":ds[-1],
      "count_over_0p1mm":sum(d>.0001 for d in ds),
      "count_over_1mm":sum(d>.001 for d in ds),"count_over_5mm":sum(d>.005 for d in ds)}

def compare(a,b):
    direct=nearest_distances(a,b)
    reverse=nearest_distances(b,a)
    return {"a_to_b":direct,"b_to_a":reverse,"symmetric_p95_m":max(direct["p95_m"],reverse["p95_m"]),"symmetric_max_m":max(direct["max_m"],reverse["max_m"])}

def negative_control():
    a=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
    from mathutils import Vector
    v=[Vector(p) for p in a]
    good=compare(v,v)
    bad=compare(v,[p+Vector((.2,0.,0.)) for p in v])
    if good["symmetric_max_m"]!=0 or bad["symmetric_max_m"]<.19:
        fail("negative control failed to detect shifted geometry")
    return bad["symmetric_max_m"]

def run(out):
    orig=bpy.data.objects.get("R036_Official_MPFB_Human")
    rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
    if not orig or orig.type!="MESH" or not rig or rig.type!="ARMATURE":
        fail("source native MPFB body/rig unavailable")
    shifts=negative_control()
    bpy.context.scene.frame_set(1)
    result={"schema":"scp.anatomy.gltf_roundtrip.v1","stage":"NARROW_MEASUREMENT_NOT_PRODUCTION_ACCEPTANCE",
      "negative_shift_control_max_m":shifts,"native_body_raw_vertices":len(orig.data.vertices),
      "native_body_evaluated_vertices":len(points(orig)),
      "profiles":{},"blender":bpy.app.version_string}
    # A/B against the first two valid GLBs: now explicitly test Blender's
    # apply-modifiers export to discover helper-mask leakage. This is a
    # separate game interchange profile, NOT a filmmaking master substitute:
    # export_apply can destroy/misrepresent shape keys.
    bpy.ops.object.select_all(action="DESELECT")
    selected=[orig,rig]+[bpy.data.objects[n] for n in ("R036_AnatomyProxy_Left","R036_AnatomyProxy_Right")]
    for o in selected:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    challenger=[("masked_four","mpfb-anatomy-masked-four.glb",False),
                ("masked_all","mpfb-anatomy-masked-all.glb",True)]
    for label,filename,allw in challenger:
        bpy.ops.export_scene.gltf(filepath=os.path.join(out,filename),export_format="GLB",
              use_selection=True,export_apply=True,export_all_influences=allw)
        if not os.path.isfile(os.path.join(out,filename)):
            fail("mask-applied GLB export missing for "+label)
    cases=[("four_influence","mpfb-official-anatomy.glb"),
      ("all_influences","mpfb-official-anatomy-allweights.glb")]+[(a,b) for a,b,_ in challenger]
    for label,filename in cases:
        path=os.path.join(out,filename)
        if not os.path.isfile(path):fail("missing source-pinned GLB "+filename)
        before=set(bpy.context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        imported=[o for o in bpy.context.scene.objects if o not in before]
        candidate=[o for o in imported if o.type=="MESH"]
        native_count=len(orig.data.vertices)
        if len(candidate)<2:fail(label+" imported fewer than two geometry objects")
        obj=max(candidate,key=lambda o:len(o.data.vertices))
        allarms=[o for o in imported if o.type=="ARMATURE"]
        if not allarms:fail(label+" no imported armature")
        if not any(m.type=="ARMATURE" for m in obj.modifiers):
            fail(label+" imported body is unskinned")
        profile={"source_glb_sha256":hashlib.sha256(open(path,"rb").read()).hexdigest(),
          "import_mesh_count":len(candidate),"import_armature_count":len(allarms),
          "body_original_vertex_count":native_count,"body_import_vertex_count":len(obj.data.vertices),
          "per_frame":{}}
        for frame in [1,12,24]:
            bpy.context.scene.frame_set(frame)
            a=points(orig);b=points(obj)
            m=compare(a,b)
            if not all(math.isfinite(v) for k in ["symmetric_p95_m","symmetric_max_m"] for v in [m[k]]):
                fail(label+" nonfinite geometry error")
            profile["per_frame"][str(frame)]=m
        # Import/export round-trip itself can change topology and material nodes:
        # geometry metrics are nearest-surface approximations, not indexed vertex equality.
        profile["poses_are_not_full_visual_acceptance"]=True
        result["profiles"][label]=profile
        for o in imported:bpy.data.objects.remove(o,do_unlink=True)
    p=result["profiles"]
    def error(label,frame):return p[label]["per_frame"][str(frame)]["symmetric_p95_m"]
    result["difference_p95_four_minus_all_m"]={str(frame):error("four_influence",frame)-error("all_influences",frame) for frame in [1,12,24]}
    result["masked_vs_unmasked_reverse_p95_m"]={
      name:{str(frame):p[name]["per_frame"][str(frame)]["b_to_a"]["p95_m"] for frame in [1,12,24]}
      for name in ["all_influences","masked_all"]}
    result["semantic_assessment"]="MEASURED_HELPER_GEOMETRY_AND_SKIN_INFLUENCE_NOT_TARGET_ENGINE_ACCEPTANCE"
    print("R036_GLTF_REIMPORT_RECEIPT "+json.dumps(result,sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    n=parse()
    run(n.out)
