"""R045 source-index-stable *synthetic* organ morphology anchor proof.

Near-surface 24-point anchors are algorithmic geometry controls, NOT anatomical
landmarks or biological organ registration. Exact official public MPFB only.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

sys.path.insert(0,os.path.dirname(__file__))
import morph_mask_preserving as core
import morph_organ_coexport as previous

FRAMES=(1,12,24)
ANCHOR_COUNT=24
IMPORT_LIMIT=0.00008


def reject(reason):
    raise RuntimeError("R045_ORGAN_MORPH_ANCHOR_HOLD "+reason)


def centroid(points):
    if not points: reject("empty anchor coordinates")
    return sum(points,Vector((0,0,0)))/len(points)


def anchor_ids(body,organ):
    b=core.evaluated(body,1)
    o=core.evaluated(organ,1)
    center=centroid(o)
    nearest=sorted(range(len(b)),key=lambda i:(b[i]-center).length_squared)[:ANCHOR_COUNT]
    if len(nearest)!=ANCHOR_COUNT or len(set(nearest))!=ANCHOR_COUNT:
        reject("invalid morph anchor uniqueness")
    return nearest


def anchor_center(body,ids,frame):
    b=core.evaluated(body,frame)
    if max(ids)>=len(b):
        reject("anatomical geometry cardinality changed")
    return centroid([b[i] for i in ids])


def create_proxy(body,organ,rig,ids,meta,side):
    base_values={k["name"]:k["value"] for k in meta if k["name"]!="Basis"}
    o=organ.copy()
    o.data=organ.data.copy()
    o.name="R045_AnchorSynthetic_"+side
    bpy.context.collection.objects.link(o)
    # Probe all active sliders as independent directional full-unit finite
    # differences at rest. Do not claim anatomically validated anchors.
    org_basis=[v.co.copy() for v in o.data.vertices]
    per_key={}
    try:
        for entry in meta:
            if entry["name"]=="Basis" or entry["mute"]:
                continue
            k=body.data.shape_keys.key_blocks[entry["name"]]
            old=float(k.value)
            lo=max(entry["slider_min"],old-.12)
            hi=min(entry["slider_max"],old+.12)
            if hi-lo<.05:
                reject("unusable shape-key finite difference range "+k.name)
            k.value=lo
            a=anchor_center(body,ids,1)
            k.value=hi
            b=anchor_center(body,ids,1)
            k.value=old
            per_unit_world=(b-a)/(hi-lo)
            per_key[entry["name"]]=o.matrix_world.inverted().to_3x3()@per_unit_world
    finally:
        for name,val in base_values.items():
            body.data.shape_keys.key_blocks[name].value=val
    if len(per_key)!=8:
        reject("eight morph channels not sampled")
    offset=sum((per_key[name]*base_values[name] for name in per_key),Vector((0,0,0)))
    basis=o.shape_key_add(name="Basis",from_mix=False)
    for i,p in enumerate(org_basis):
        basis.data[i].co=p-offset
    for entry in meta:
        name=entry["name"]
        if name=="Basis":
            continue
        sk=o.shape_key_add(name=name,from_mix=False)
        delta=per_key.get(name,Vector((0,0,0)))
        for i,p in enumerate(org_basis):
            sk.data[i].co=p-offset+delta
        sk.value=base_values[name]
        sk.slider_min=entry["slider_min"]
        sk.slider_max=entry["slider_max"]
        sk.mute=entry["mute"]
    if len(o.data.shape_keys.key_blocks)!=len(meta):
        reject("synthetic proxy morph cardinality mismatch")
    if not any(m.type=="ARMATURE" and m.object==rig for m in o.modifiers):
        reject("proxy lost original armature link")
    return o,{"anchor_indices":ids,
              "anchor_count":len(ids),
              "per_key_local_shift_m":{n:[float(c) for c in v] for n,v in per_key.items()},
              "nonzero_morphs":sum(v.length>1e-8 for v in per_key.values())}


def export_scene(body,rig,proxies,root):
    dest=os.path.join(root,"r045-morph-anchored-proxies.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [body,rig]+proxies: obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=dest,export_format="GLB",
        use_selection=True,export_all_influences=True,export_morph=True)
    if not os.path.isfile(dest) or os.stat(dest).st_size<5000:
        reject("missing actual morphed organ GLB")
    before={o.as_pointer() for o in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=dest)
    new=[o for o in bpy.data.objects if o.as_pointer() not in before]
    arms=[o for o in new if o.type=="ARMATURE"]
    if len(arms)!=1 or len(arms[0].data.bones)!=len(rig.data.bones):
        reject("imported synthetic rig does not match original")
    imp=[]
    for proxy in proxies:
        candidates=[o for o in new if o.type=="MESH" and proxy.name in o.name]
        if len(candidates)!=1:
            reject("import lost synthetic morph proxy "+proxy.name)
        candidate=candidates[0]
        a=[k.name for k in proxy.data.shape_keys.key_blocks]
        b=[k.name for k in candidate.data.shape_keys.key_blocks] if candidate.data.shape_keys else []
        if a!=b:
            reject("import dropped synthetic organ morph shape keys")
        if not any(m.type=="ARMATURE" and m.object in arms for m in candidate.modifiers):
            reject("import synthetic organ lacks skin rig")
        imp.append(candidate)
    return imp,{"sha256":core.hfile(dest),"bytes":os.stat(dest).st_size,
                "bones":len(arms[0].data.bones),
                "imported_proxy_morph_counts":[len(p.data.shape_keys.key_blocks) for p in imp]}


def variant(meta):
    return [("baseline",{})]+previous.variants(meta)


def set_values(obj,base,changes):
    if obj.data.shape_keys is None:
        reject("source or candidate lacks named morphs")
    for name,val in base.items():
        sk=obj.data.shape_keys.key_blocks.get(name)
        if sk is None: reject("missing morph "+name+" in "+obj.name)
        sk.value=changes.get(name,val)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    root=os.path.abspath(args.out)
    path=os.path.join(root,"mpfb-official-anatomy.blend")
    if not os.path.isfile(path): reject("missing original saved master")
    original_sha=core.hfile(path)
    body=bpy.data.objects.get("R036_Official_MPFB_Human")
    rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
    originals=[bpy.data.objects.get("R036_AnatomyProxy_Left"),
               bpy.data.objects.get("R036_AnatomyProxy_Right")]
    if body is None or rig is None or any(o is None for o in originals):
        reject("source anatomy/rig/body unavailable")
    meta=core.keymeta(body)
    source_values={x["name"]:x["value"] for x in meta if x["name"]!="Basis"}
    editable,struct=core.remap_editable(body,rig)
    refs=[anchor_ids(body,o) for o in originals]
    generated=[]
    maps=[]
    for side,src,ids in zip(("Left","Right"),originals,refs):
        candidate,info=create_proxy(body,src,rig,ids,meta,side)
        generated.append(candidate)
        maps.append(info)
    imported,receipt=export_scene(editable,rig,generated,root)
    if not any(m["nonzero_morphs"]>=2 for m in maps):
        reject("no meaningful synthetic organ morphology response")
    records=[]
    # Define world-space placement delta at each frame relative to source
    # anchors. This is a measured hypothesis, NOT an actual organ fit.
    baseline_anchors={}
    baseline_proxy={}
    for frame in FRAMES:
        baseline_anchors[frame]=[anchor_center(body,ids,frame) for ids in refs]
        baseline_proxy[frame]=[centroid(core.evaluated(p,frame)) for p in generated]
    try:
        for label,changes in variant(meta):
            for obj in (body,editable,*generated,*imported):
                set_values(obj,source_values,changes)
            per_frame=[]
            for frame in FRAMES:
                errors=[]
                imported_errors=[]
                measured=[]
                for j,(gen,imp) in enumerate(zip(generated,imported)):
                    anchor_delta=anchor_center(body,refs[j],frame)-baseline_anchors[frame][j]
                    center_now=centroid(core.evaluated(gen,frame))
                    proxy_delta=center_now-baseline_proxy[frame][j]
                    fit_error=float((proxy_delta-anchor_delta).length)
                    err=previous.test_points(gen,imp,frame,IMPORT_LIMIT,"synthetic organ glTF morph parity")
                    errors.append(fit_error)
                    imported_errors.append(float(err))
                    measured.append(float(anchor_delta.length))
                per_frame.append({"frame":frame,"attachment_delta_error_m":errors,
                    "imported_proxy_geometry_error_m":imported_errors,
                    "native_anchor_movement_m":measured})
            records.append({"variant":label,"changes":len(changes),"frames":per_frame})
    finally:
        for obj in (body,editable,*generated,*imported):
            set_values(obj,source_values,{})
    if original_sha!=core.hfile(path): reject("immutable source master changed")
    if core.keymeta(body)!=meta: reject("source morph metadata not restored")
    attachment_errors=[err for record in records for f in record["frames"]
                       for err in f["attachment_delta_error_m"]]
    movements=[err for record in records for f in record["frames"]
               for err in f["native_anchor_movement_m"]]
    observed_motion=max(movements)
    if observed_motion<=1e-5: reject("shape DOE did not produce measurable anchored body motion")
    if any(not math.isfinite(x) for x in attachment_errors):
        reject("nonfinite organ-to-skin attachment difference")
    maxerr=max(attachment_errors)
    # Low thresholds are only safety tripwires; do not certify anatomical
    # registration. Even zero is no real-organ anatomical truth.
    if maxerr > .05:
        reject("gross (>5cm) synthetic anchor-to-organ mismatch: "+str(maxerr))
    out={"schema":"r045.mpfb.synthetic-morph-anchor.v1",
        "status":"PASS_NARROW_ALGORITHMIC_ANCHOR_DIAGNOSTIC",
        "source_sha256":original_sha,"source_unmodified":True,
        "frames":list(FRAMES),"scenarios":len(records),
        "anchor_maps":maps,"export":receipt,
        "max_anchor_response_m":observed_motion,
        "max_anchor_proxy_response_error_m":maxerr,
        "max_imported_proxy_surface_error_m":max(
            e for row in records for frame in row["frames"]
            for e in frame["imported_proxy_geometry_error_m"]),
        "measurements":records,
        "limitations":"Approximate nearest-skin anchor, two nonanatomical ellipsoids, no anatomical organ location/physical deformation/multi-joint engine parity; no CharacterPack acceptance",
        "release_decision":"HOLD"}
    with open(os.path.join(root,"r045-organ-morph-anchor.json"),"w",encoding="utf-8") as handle:
        json.dump(out,handle,indent=2,sort_keys=True)
    print("R045_ORGAN_ANCHOR_RECEIPT "+json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()
