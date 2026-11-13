"""Experimental source-mesh-barycentric attachment transfer for actual CC0 MPFB humans.

Use the exact *original* source body evaluated triangles as a correspondence
cage to drive every accessory's vertices after a shape-key body morphology.
This attempts to correct the proven fixed-in-world accessory defect. This
is a NON-PRODUCTION candidate: no watertight collision, precise anatomical
rigging, hair simulation, tissue physics or photoreal acceptance is asserted.
No original assets are overwritten. Public and synthetic only.
"""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys

import bpy
from mathutils import Matrix, Vector, geometry
from mathutils.bvhtree import BVHTree
import numpy as np

def sha(path):
    h=sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def triangles(mesh):
    faces=[]
    for polygon in mesh.polygons:
        v=[int(x) for x in polygon.vertices]
        for i in range(1,len(v)-1):
            faces.append((v[0],v[i],v[i+1]))
    return np.asarray(faces,dtype=np.int32)

def original_export(a):
    sex=a.sex
    assert Path(bpy.data.filepath).resolve()==a.original_blend.resolve()
    obj=bpy.data.objects["R014_"+sex+"_textured_body"]
    assert obj.type=="MESH"
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=ev.to_mesh()
    try:
        verts=np.asarray([list(v.co) for v in mesh.vertices],dtype=np.float64)
        tri=triangles(mesh)
        assert len(verts)>12000 and len(tri)>10000
        assert np.isfinite(verts).all()
        a.out.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(a.out,vertices=verts,triangles=tri,
                           matrix=np.asarray([list(row) for row in obj.matrix_world],dtype=np.float64))
        receipt={
           "schema":"r014.cc0.original_body_evaluated_surface.v1",
           "sex_macro":sex,"original_blend_sha256":sha(a.original_blend),
           "source_evaluated_vertices":len(verts),"triangles":len(tri),
           "source_original_archive":"official CC0 MPFB+MAKESKIN public source, 43207664661",
           "npz_sha256":sha(a.out),"source_float_precision":"float64",
           "stage":"baseline original Blender 4.5.16 actual dependency graph",
           "no_likeness":True,"merge_release":"HOLD"
        }
        a.out.with_suffix(".json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
        print("R014_ATTACHMENT_ORIGINAL_EXPORT",json.dumps(receipt,sort_keys=True))
    finally:ev.to_mesh_clear()

def descendant(obj,root):
    seen=set()
    while obj and obj.name not in seen:
        if obj is root:return True
        seen.add(obj.name);obj=obj.parent
    return False

def sample_sha(obj,mesh,limit=512):
    verts=mesh.vertices
    h=sha256()
    n=min(len(verts),limit)
    indices=sorted({int(i*(len(verts)-1)/(n-1)) for i in range(n)}) if n>1 else [0]
    for i in indices:
        w=obj.matrix_world@verts[i].co
        h.update(",".join(f"{float(c):.7f}" for c in w).encode("ascii"))
        h.update(b";")
    return h.hexdigest()

def fit_with_rigged_scene(a):
    sex=a.sex
    assert Path(bpy.data.filepath).resolve()==a.morphed_blend.resolve()
    receipt=json.loads(a.morph_receipt.read_text())
    source=json.loads(a.source_receipt.read_text())
    assert receipt["sex_macro_label"]==sex
    assert receipt["status"]=="PASS_SOURCE_NATIVE_CC0_MORPH_MOTION_RENDER_STRUCTURAL_ONLY"
    assert receipt["editable_blend"]["sha256"]==sha(a.morphed_blend)
    assert source["sex_macro"]==sex and source["npz_sha256"]==sha(a.reference)
    pack=np.load(a.reference,allow_pickle=False)
    oldcoords=np.asarray(pack["vertices"],dtype=np.float64)
    origtri=np.asarray(pack["triangles"],dtype=np.int32)
    old_world=Matrix(pack["matrix"].tolist())
    old_inv=old_world.inverted_safe()
    body=bpy.data.objects["R014_"+sex+"_textured_body"]
    rig=bpy.data.objects["R014_"+sex+"_textured_rig"]
    assert body.type=="MESH" and rig.type=="ARMATURE"
    assert len(body.data.vertices)==19158 and len(rig.data.bones)==163
    scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    eval_body=body.evaluated_get(dg)
    mesh=eval_body.to_mesh()
    try:
        newcoords=np.asarray([list(v.co) for v in mesh.vertices],dtype=np.float64)
        newtri=triangles(mesh)
        assert newcoords.shape==oldcoords.shape and np.array_equal(newtri,origtri), "MISMATCHED_NATIVE_MESH_TRIANGLE_CORRESPONDENCE"
        assert np.isfinite(newcoords).all()
        delta=np.linalg.norm(newcoords-oldcoords,axis=1)
        assert delta.max()>0.005,"NO_REAL_BODY_SHAPE_DELTA"
        original_bvh=BVHTree.FromPolygons([Vector(v) for v in oldcoords],
                     [tuple(int(x) for x in t) for t in origtri],
                     all_triangles=True,epsilon=0.0)
        target_bvh=BVHTree.FromPolygons([Vector(v) for v in newcoords],
                     [tuple(int(x) for x in t) for t in newtri],
                     all_triangles=True,epsilon=0.0)
        newmat=body.matrix_world.copy()
        objects=[]
        for obj in sorted(bpy.data.objects,key=lambda x:x.name):
            if obj.type!="MESH" or obj is body:continue
            related=(obj.name.startswith("R014_"+sex+"_") or
                     descendant(obj,rig) or descendant(obj,body))
            if related:objects.append(obj)
        assert len(objects)>=5,"MISSING_ORIGINAL_CC0_ACCESSORIES"
        results=[]
        for accessory in objects:
            shape=accessory.data.shape_keys
            evaluated=accessory.evaluated_get(dg)
            current=evaluated.to_mesh()
            try:
                n_raw=len(accessory.data.vertices)
                if n_raw<1:continue
                if len(current.vertices)!=n_raw:
                    results.append({"name":accessory.name,"status":"HOLD_EVALUATED_RAW_TOPOLOGY_DIFFERENT",
                      "evaluated_vertices":len(current.vertices),"raw_vertices":n_raw})
                    continue
                sha_before=sample_sha(evaluated,current)
            finally:evaluated.to_mesh_clear()
            inv_accessory=accessory.matrix_world.inverted_safe()
            displacement=[]
            baseline_gap=[]
            current_gap=[]
            for vert in accessory.data.vertices:
                w=accessory.matrix_world@vert.co
                p=old_inv@w
                closest=original_bvh.find_nearest(p)
                anchor,normal,tri_index,dist=closest
                if anchor is None or tri_index is None:
                    raise RuntimeError("NO_ORIGINAL_SOURCE_BODY_CORRESPONDENCE")
                ids=origtri[tri_index]
                anchor_new=geometry.barycentric_transform(
                    anchor,
                    *[Vector(oldcoords[int(i)]) for i in ids],
                    *[Vector(newcoords[int(i)]) for i in ids])
                disp_world=(newmat@anchor_new)-(old_world@anchor)
                dv=inv_accessory.to_3x3()@disp_world
                assert all(math.isfinite(float(x)) for x in dv),"NONFINITE_TRANSFER"
                displacement.append(dv.copy())
                baseline_gap.append(float(dist))
                morph_nearest=target_bvh.find_nearest(newmat.inverted_safe()@w)
                current_gap.append(float(morph_nearest[3]))
            max_d=max(v.length for v in displacement)
            assert max_d<2.0,"IMPLAUSIBLE_CORRECTIVE_VERTEX_DELTA"
            keys=shape.key_blocks if shape else None
            if keys:
                for key in keys:
                    assert len(key.data)==len(displacement)
                    for i,v in enumerate(displacement):key.data[i].co+=v
            else:
                for i,v in enumerate(displacement):accessory.data.vertices[i].co+=v
            accessory.data.update()
            bpy.context.view_layer.update()
            evaluated2=accessory.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh2=evaluated2.to_mesh()
            try:
                sha_after=sample_sha(evaluated2,mesh2)
                assert sha_after!=sha_before,("SOURCE_ASSET_STILL_UNCHANGED",accessory.name)
                indices=sorted({int(i*(len(mesh2.vertices)-1)/(min(len(mesh2.vertices),512)-1))
                              for i in range(min(len(mesh2.vertices),512))}) if len(mesh2.vertices)>1 else [0]
                after_gap=[float(target_bvh.find_nearest(newmat.inverted_safe()@(evaluated2.matrix_world@mesh2.vertices[i].co))[3])
                           for i in indices]
            finally:evaluated2.to_mesh_clear()
            info={
               "name":accessory.name,"status":"TRANSFERRED_REAL_SOURCE_MESH_BARYCENTRIC",
               "raw_vertices":n_raw,
               "shape_keys_adjusted":0 if not keys else len(keys),
               "world_sample_sha256_before":sha_before,
               "world_sample_sha256_after":sha_after,
               "max_vertex_displacement_native_units":round(float(max_d),7),
               "mean_source_reference_body_gap_native":round(float(np.mean(baseline_gap)),7),
               "mean_before_transfer_target_gap_native":round(float(np.mean(current_gap)),7),
               "mean_after_transfer_target_gap_native":round(float(np.mean(after_gap)),7),
               "geometry_acceptance":"HOLD_NONWATERTIGHT_NEAREST_DISTANCE_PROXY",
            }
            results.append(info)
        assert len([x for x in results if x["status"]=="TRANSFERRED_REAL_SOURCE_MESH_BARYCENTRIC"])>=5
        current_objects=[x for x in results if x["status"]=="TRANSFERRED_REAL_SOURCE_MESH_BARYCENTRIC"]
        # This is an *instrumented candidate*, not proof that every asset fits;
        # matching source distances often improves but a hair/eye region may not.
        improvement_count=sum(
            abs(x["mean_after_transfer_target_gap_native"]-x["mean_source_reference_body_gap_native"]) <
            abs(x["mean_before_transfer_target_gap_native"]-x["mean_source_reference_body_gap_native"])
            for x in current_objects)
        result={
          "schema":"r014.cc0.barycentric_attachment_transfer_candidate.v1",
          "status":"PASS_EXPERIMENTAL_NATIVE_MESH_TRANSFER_AND_REVIEW_FILES_ONLY",
          "sex_macro":sex,"source_mpfb":"6ff1eb358f6c1959ced77e79e6dd2406d9a71f49",
          "source_original_blend_sha256":source["original_blend_sha256"],
          "source_morphed_blend_sha256":sha(a.morphed_blend),
          "source_body_evaluated_triangles":len(origtri),
          "original_evaluated_vertices":len(oldcoords),
          "target_evaluated_vertices":len(newcoords),
          "original_to_target_body_max_vertex_delta":round(float(delta.max()),7),
          "real_accessory_meshes_evaluated":len(results),
          "transferred_accessory_meshes":len(current_objects),
          "distance_proxy_improved_asset_count":improvement_count,
          "transfers":results,
          "disclaimers":["candidate mesh deformation only, not material, UV, normals or hair simulation approval",
            "source nearest body surface does not certify watertight external anatomy or collision",
            "assumes source/target MPFB evaluated vertex-index and triangle correspondence",
            "source custom teeth/tongue/eye topology not vetted for physiological motion",
            "no 4K/motion/rig/viseme/identity production acceptance"],
          "geometry_approval":"HOLD",
          "merge_release":"HOLD"
        }
    finally:eval_body.to_mesh_clear()
    a.out.mkdir(parents=True,exist_ok=True)
    scene.frame_set(1)
    bpy.ops.file.pack_all()
    native=a.out/("R014_"+sex+"_experimental_accessory_transfer.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    result["native_blend"]={"name":native.name,"bytes":native.stat().st_size,"sha256":sha(native)}
    # Standalone native cycles visual technical evidence.
    scene.render.engine="CYCLES";scene.cycles.device="CPU";scene.cycles.samples=7
    scene.render.threads_mode="FIXED";scene.render.threads=4
    scene.render.resolution_x=448;scene.render.resolution_y=576
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    camera=bpy.data.objects.get("R014_CC0_Morph_Camera_"+sex)
    if camera is None:camera=scene.camera
    assert camera and camera.type=="CAMERA"
    scene.camera=camera
    renders=[]
    for label,frame in (("rest",1),("posed",8)):
        scene.frame_set(frame)
        output=a.out/(sex+"_experimental_"+label+".png")
        scene.render.filepath=str(output)
        bpy.ops.render.render(write_still=True)
        assert output.stat().st_size>3000
        renders.append({"name":output.name,"sha256":sha(output)})
    result["real_source_blender_cycles_stills"]=renders
    out=a.out/"candidate_transfer_receipt.json"
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("R014_ATTACHMENT_TRANSFER",json.dumps({
        "status":result["status"],"sex_macro":sex,
        "transferred":result["transferred_accessory_meshes"],
        "improved_proxy":result["distance_proxy_improved_asset_count"],
        "largest_displacement":max(x["max_vertex_displacement_native_units"] for x in current_objects),
        "images":[x["name"] for x in renders],
        "native_blend_sha256":result["native_blend"]["sha256"]
    },sort_keys=True))

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--mode",choices=("export","apply"),required=True)
    pa.add_argument("--sex",choices=("female","male"),required=True)
    pa.add_argument("--original-blend",type=Path)
    pa.add_argument("--morphed-blend",type=Path)
    pa.add_argument("--reference",type=Path)
    pa.add_argument("--source-receipt",type=Path)
    pa.add_argument("--morph-receipt",type=Path)
    pa.add_argument("--out",type=Path,required=True)
    a=pa.parse_args(sys.argv[sys.argv.index("--")+1:])
    if a.mode=="export":
        assert a.original_blend
        original_export(a)
    else:
        assert a.morphed_blend and a.reference and a.source_receipt and a.morph_receipt
        fit_with_rigged_scene(a)

if __name__=="__main__":main()
