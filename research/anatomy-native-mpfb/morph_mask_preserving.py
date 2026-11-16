"""R043: Preserve MPFB source shape keys and indexed ancestry when removing helper mask.

Builds a disposable *editable* derived mesh with bmesh edit-mode deletion,
not a baked, non-editable clone. Public official MPFB only. No product release.
"""
import argparse
import bmesh
import hashlib
import json
import math
import os
import sys
from mathutils.kdtree import KDTree
import bpy

FRAMES=(1,12,24)
MATCH_LIMIT_M=0.00002
IMPORT_LIMIT_M=0.00008

def fail(reason):
    raise RuntimeError("R043_MORPH_MASK_HOLD "+reason)

def hfile(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""): h.update(part)
    return h.hexdigest()

def evaluated(obj,frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    e=obj.evaluated_get(dg)
    mesh=e.to_mesh()
    try:
        return [e.matrix_world@v.co for v in mesh.vertices]
    finally:
        e.to_mesh_clear()

def nearest(a,b):
    if not a or not b: fail("empty evaluated body")
    tree=KDTree(len(b))
    for i,p in enumerate(b): tree.insert(p,i)
    tree.balance()
    ds=[]
    for p in a:
        _,_,d=tree.find(p)
        if not math.isfinite(d): fail("nonfinite topology residual")
        ds.append(float(d))
    return {"count":len(ds),"max_m":max(ds),"mean_m":sum(ds)/len(ds),
            "p95_m":sorted(ds)[max(0,math.ceil(len(ds)*.95)-1)]}

def check_surface(original,derived,frame,threshold,label):
    a=evaluated(original,frame)
    b=evaluated(derived,frame)
    report={"a_to_b":nearest(a,b),"b_to_a":nearest(b,a),
            "original_evaluated_vertices":len(a),"candidate_evaluated_vertices":len(b)}
    if max(report["a_to_b"]["max_m"],report["b_to_a"]["max_m"])>threshold:
        fail(label+" failed at frame "+str(frame)+" residual "+str(report))
    return report

def mask_members(body,mask):
    if mask.mode!="VERTEX_GROUP" or not mask.vertex_group:
        fail("unsupported MASK mode or unnamed group")
    group=body.vertex_groups.get(mask.vertex_group)
    if group is None: fail("mask vertex group not found")
    keep=[]
    excluded=[]
    for v in body.data.vertices:
        weight=next((x.weight for x in v.groups if x.group==group.index),0.0)
        # Matches Blender Mask vertex-group threshold semantics; independently
        # verify cardinality against real evaluated source before acceptance.
        selected=weight>mask.threshold
        if mask.invert_vertex_group: selected=not selected
        (keep if selected else excluded).append(v.index)
    print("R043_MASK_SOURCE_PARTITION", json.dumps({
        "group": mask.vertex_group, "threshold": float(mask.threshold),
        "invert": bool(mask.invert_vertex_group), "kept": len(keep),
        "deleted": len(excluded), "total": len(body.data.vertices)}, sort_keys=True))
    if not keep or not excluded: fail("empty mask keep/delete partition")
    return keep,excluded

def keymeta(obj):
    keys=obj.data.shape_keys
    if not keys or not keys.use_relative: fail("expected source relative shape keys")
    return [{"name":k.name,"value":float(k.value),"slider_min":float(k.slider_min),
             "slider_max":float(k.slider_max),"mute":bool(k.mute),
             "vertex_group":k.vertex_group,
             "relative":k.relative_key.name if k.relative_key else None}
            for k in keys.key_blocks]

def remap_editable(body,rig):
    source_keys=keymeta(body)
    masks=[m for m in body.modifiers if m.type=="MASK"]
    if len(masks)!=1 or masks[0].name!="Hide helpers": fail("unsupported source mask stack")
    mask=masks[0]
    keep,remove=mask_members(body,mask)
    original_vertices=len(body.data.vertices)
    orig_frame=evaluated(body,1)
    if len(keep)!=len(orig_frame):
        fail("mask vertex partition disagrees with native evaluated geometry: "+
             str(len(keep))+" != "+str(len(orig_frame)))
    clone=body.copy()
    clone.data=body.data.copy()
    clone.name="R043_EditableMask_MPFB_Body"
    bpy.context.collection.objects.link(clone)
    if clone.data.shape_keys is body.data.shape_keys:
        fail("clone did not isolate source morph data")
    # Explicit stable raw source-point identity survives Blender edit-mode
    # topology deletion as a per-vertex Blender INT attribute.
    attr=clone.data.attributes.new("r043_source_id","INT","POINT")
    for i,item in enumerate(attr.data): item.value=i
    bpy.ops.object.select_all(action="DESELECT")
    clone.select_set(True)
    bpy.context.view_layer.objects.active=clone
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        bm=bmesh.from_edit_mesh(clone.data)
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        deleted=set(remove)
        geom=[v for v in bm.verts if v.index in deleted]
        if len(geom)!=len(remove): fail("BMesh index lineage not stable on source")
        bmesh.ops.delete(bm,geom=geom,context="VERTS")
        bmesh.update_edit_mesh(clone.data,loop_triangles=True,destructive=True)
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    if len(clone.data.vertices)!=len(keep):
        fail("masked source topology cardinality did not match")
    identities=clone.data.attributes.get("r043_source_id")
    if identities is None or identities.domain!="POINT":
        fail("lost source index point attribute")
    ancestry=[int(x.value) for x in identities.data]
    if sorted(ancestry)!=keep:
        fail("masked edited topology ancestry disagrees with source mask")
    # Remove only derived mask; preserve source object's modifier and source .blend.
    dmask=clone.modifiers.get(mask.name)
    if dmask is None: fail("source mask missing on derived mesh")
    clone.modifiers.remove(dmask)
    arms=[m for m in clone.modifiers if m.type=="ARMATURE" and m.object==rig]
    if len(arms)!=1 or len(clone.data.vertices)!=len(ancestry):
        fail("lost native armature or vertex source correspondence")
    if keymeta(clone)!=source_keys:
        fail("shape key names, values, relative ancestry or sliders changed")
    raw_keys=body.data.shape_keys.key_blocks
    filtered_keys=clone.data.shape_keys.key_blocks
    max_key_err=0.0
    for i,source_id in enumerate(ancestry):
        for key in raw_keys:
            max_key_err=max(max_key_err,
                float((filtered_keys[key.name].data[i].co-key.data[source_id].co).length))
    if max_key_err>1e-6: fail("shape-key per-index ancestry/delta is not preserved")
    # Exact skinning weights by matched stable raw vertex ID.
    max_weight_diff=0.0
    count=0
    for i,source_id in enumerate(ancestry):
        expected={g.group:float(g.weight) for g in body.data.vertices[source_id].groups}
        actual={g.group:float(g.weight) for g in clone.data.vertices[i].groups}
        if expected.keys()!=actual.keys(): fail("vertex group weight group set changed")
        for g,w in actual.items():
            max_weight_diff=max(max_weight_diff,abs(w-expected[g]))
            count+=1
    if max_weight_diff>1e-7: fail("skin weights changed on editable derived mesh")
    if len(clone.data.uv_layers)!=len(body.data.uv_layers):
        fail("UV layer cardinality changed")
    # Polygon UV loop fidelity can be verified with stable mapped corner
    # identities + ordered original polygon vertex sequence.
    origpoly={}
    keep_set=set(keep)
    for p in body.data.polygons:
        raw=tuple(p.vertices)
        if all(j in keep_set for j in raw):
            if raw in origpoly: fail("ambiguous original polygon ordering")
            origpoly[raw]=p
    if len(origpoly)!=len(clone.data.polygons):
        fail("derived polygon count differs from masked original polygon selection")
    max_uv_error=0.0
    for p in clone.data.polygons:
        raw=tuple(ancestry[j] for j in p.vertices)
        source_p=origpoly.get(raw)
        if source_p is None: fail("lost ordered source triangle/quad topology")
        if p.material_index!=source_p.material_index:
            fail("source polygon material index changed")
        for layer_id in range(len(body.data.uv_layers)):
            src_uv=body.data.uv_layers[layer_id]
            dst_uv=clone.data.uv_layers[layer_id]
            for i,li in enumerate(p.loop_indices):
                sli=source_p.loop_indices[i]
                max_uv_error=max(max_uv_error,
                    float((dst_uv.data[li].uv-src_uv.data[sli].uv).length))
    if max_uv_error>1e-7: fail("original per-loop UV changed under mask")
    return clone,{"source_raw_vertices":original_vertices,"masked_vertices":len(ancestry),
        "removed_vertices":len(remove),"shape_keys_retained":len(filtered_keys),
        "max_shape_coordinate_error_m":max_key_err,
        "max_vertex_weight_error":max_weight_diff,"weights_checked":count,
        "uv_layers_checked":len(body.data.uv_layers),
        "polygons_checked":len(origpoly),"max_uv_error":max_uv_error,
        "source_ancestry_unique":len(set(ancestry))==len(ancestry),
        "mask_mode":mask.mode,"mask_group":mask.vertex_group,
        "mask_threshold":float(mask.threshold),
        "mask_inverted":bool(mask.invert_vertex_group)}

def export_import(body,rig,root):
    dest=os.path.join(root,"r043-editable-mask-allweights.glb")
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=dest,export_format="GLB",
        use_selection=True,export_all_influences=True,export_morph=True)
    if not os.path.isfile(dest) or os.stat(dest).st_size<2000: fail("GLB absent")
    previous={x.as_pointer() for x in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=dest)
    new=[x for x in bpy.data.objects if x.as_pointer() not in previous]
    bodylist=[x for x in new if x.type=="MESH" and "R043_EditableMask_MPFB_Body" in x.name]
    arms=[x for x in new if x.type=="ARMATURE"]
    if len(bodylist)!=1 or len(arms)!=1: fail("morph GLB importer body/rig missing")
    obj=bodylist[0]
    if not any(m.type=="ARMATURE" and m.object==arms[0] for m in obj.modifiers):
        fail("morph GLB lost skinned armature")
    if len(arms[0].data.bones)!=len(rig.data.bones):
        fail("morph GLB dropped source rig bones")
    src=keymeta(body)
    imported=keymeta(obj)
    if len(src)!=len(imported):
        fail("morph GLB imported different shape-key count: "+
             str(len(src))+" vs "+str(len(imported)))
    src_names=[k["name"] for k in src]
    imp_names=[k["name"] for k in imported]
    if src_names!=imp_names:
        fail("morph GLB changed shape-key names or ordering: "+str(imp_names))
    return obj,new,{"sha256":hfile(dest),"size_bytes":os.stat(dest).st_size,
        "imported_vertices":len(obj.data.vertices),
        "imported_shape_keys":imp_names,
        "imported_rig_bones":len(arms[0].data.bones)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    opts=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    root=os.path.abspath(opts.out)
    original=os.path.join(root,"mpfb-official-anatomy.blend")
    if not os.path.isfile(original): fail("missing original persistent source scene")
    before=hfile(original)
    body=bpy.data.objects.get("R036_Official_MPFB_Human")
    rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
    if not body or not rig: fail("official source body/rig unavailable")
    original_key_meta=keymeta(body)
    clone,checks=remap_editable(body,rig)
    parity={}
    for f in FRAMES:
        parity[str(f)]=check_surface(body,clone,f,MATCH_LIMIT_M,"morph-preserving masked clone")
    imported,_,export=export_import(clone,rig,root)
    baseline={}
    for f in FRAMES:
        baseline[str(f)]=check_surface(body,imported,f,IMPORT_LIMIT_M,"morph+skin GLB")
    # Treat source shape value variation as a first-class invariant.
    variations={}
    active=[k for k in original_key_meta if k["name"]!="Basis" and not k["mute"]]
    if len(active)<2: fail("not enough editable source shape controls to qualify")
    sample=active[:3]
    for item in sample:
        name=item["name"]
        changed=min(item["slider_max"],item["value"]+0.08)
        if abs(changed-item["value"])<.001:
            changed=max(item["slider_min"],item["value"]-.08)
        if abs(changed-item["value"])<.001:
            fail("cannot move selected source morph")
        try:
            for obj in (body,clone,imported):
                obj.data.shape_keys.key_blocks[name].value=changed
            values={}
            for f in (1,24):
                values[str(f)]={
                    "native_to_editable":check_surface(body,clone,f,MATCH_LIMIT_M,"morph-variation clone"),
                    "native_to_imported":check_surface(body,imported,f,IMPORT_LIMIT_M,"morph-variation GLB"),
                }
            variations[name]={"original_value":item["value"],"challenger_value":changed,
                "frame_parity":values}
        finally:
            for obj in (body,clone,imported):
                obj.data.shape_keys.key_blocks[name].value=item["value"]
    if keymeta(body)!=original_key_meta:
        fail("source morph values/slider limits not restored")
    if before!=hfile(original): fail("original source .blend bytes mutated")
    result={"schema":"r043.mpfb.morph-mask-retained.v1",
        "status":"PASS_NARROW_EDITABLE_MASKED_DERIVATIVE",
        "source_sha256":before,"source_unchanged":True,"cloned_mesh_checks":checks,
        "baseline_native_vs_clone":parity,"baseline_native_vs_glb":baseline,
        "export":export,"morph_variations":variations,
        "rights":"OFFICIAL_PINNED_PUBLIC_MPFB_ORIGINAL_SYNTHETIC",
        "limits":"NOT CANONICAL CharacterPack; no engine runtime, real anatomy, physics, UV material appearance or two-person film",
        "release_decision":"HOLD"}
    out=os.path.join(root,"r043-editable-morph-mask-diagnostic.json")
    with open(out,"w",encoding="utf-8") as f: json.dump(result,f,indent=2,sort_keys=True)
    print("R043_MORPH_MASK_RECEIPT "+json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
