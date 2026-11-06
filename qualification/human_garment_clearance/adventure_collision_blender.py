#!/usr/bin/env python3
"""Read-only Blender 4.5 source-original, actual 72-frame garment/body crossing witness.

Reuse the evaluated-mesh/edge-stretch method of separate owner PR #303's
wardrobe_deformation_blender_v2.py, but inspect actual new style_top/style_bottom
from source-pinned #338 strict portable GLB. This is an intersection proxy only.
Cloth/body containment, garment ease, body continuity, physics and visual
acceptance are NOT established by an empty BVH surface intersection set.
"""
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

ACTORS=("AsterOriginal","JuniperOriginal")
SLOTS=("body","style_top","style_bottom")
SCHEMA="scp.r009.adventure_body_surface_crossings.v1"


def selftest():
    # Mutually intersecting orthogonal triangles, separated triangles,
    # and entirely contained disjoint triangle surfaces. The containment
    # counterexample MUST remain UNKNOWN, rather than falsely accepted.
    a=BVHTree.FromPolygons(
        [(-1.,-1.,0.), (1.,-1.,0.), (0.,1.,0.)], [(0,1,2)],
        all_triangles=True)
    crossing=BVHTree.FromPolygons(
        [(0.,-1.,-.5),(0.,1.,-.5),(0.,0.,.5)], [(0,1,2)],
        all_triangles=True)
    separate=BVHTree.FromPolygons(
        [(-1.,-1.,2.), (1.,-1.,2.), (0.,1.,2.)], [(0,1,2)],
        all_triangles=True)
    if not a.overlap(crossing):
        raise RuntimeError("BVH_CROSSING_FALSE_NEGATIVE")
    if a.overlap(separate):
        raise RuntimeError("BVH_SEPARATE_FALSE_POSITIVE")
    # A simple 2-triangle open surface cannot detect full volumetric
    # enclosure. Keep any apparently zero intersection as UNKNOWN.
    if height_bin(1.32)!="1.25-1.45" or height_bin(.72)!="0.60-0.85":
        raise RuntimeError("BLENDER_WORLD_Z_HEIGHT_BINS_INVALID")
    print(json.dumps({
        "schema":SCHEMA+".selftest",
        "crossing_triangles":"DETECTED",
        "separated_triangles":"NO_SURFACE_CROSSING",
        "volume_containment":"UNKNOWN_UNMEASURED",
        "garment_clearance_accepted":False,
    },sort_keys=True))


def mesh_index():
    found={}
    for obj in bpy.data.objects:
        if obj.type!="MESH" or "_Wardrobe_" not in obj.name:
            continue
        actor,slot=obj.name.split("_Wardrobe_",1)
        slot=slot.split(".")[0]
        if actor not in ACTORS:
            raise RuntimeError("UNEXPECTED_WARDROBE_ACTOR:"+actor)
        key=(actor,slot)
        if key in found:
            raise RuntimeError("DUPLICATE_GARMENT_SLOT:"+str(key))
        found[key]=obj
    if set(found)!={(a,s) for a in ACTORS for s in
                     ("body","hair","footwear","style_top","style_bottom")
                     + (("accessory",) if a=="AsterOriginal" else ())}:
        raise RuntimeError("STRICT_PORTABLE_LAYERS_DRIFT:"+
                           repr(sorted(found)))
    for actor in ACTORS:
        for slot in SLOTS:
            o=found[(actor,slot)]
            mods=[m for m in o.modifiers if m.type=="ARMATURE"]
            if len(mods)!=1 or mods[0].object is None or (
                    len(mods[0].object.data.bones)!=35):
                raise RuntimeError("SOURCE_OR_SKIN_MODIFIER_INVALID:"+actor+":"+slot)
            if len(o.data.polygons)==0 or len(o.data.vertices)==0:
                raise RuntimeError("SOURCE_EMPTY_LAYER")
            for v in o.data.vertices:
                weights=[w.weight for w in v.groups]
                if not weights or abs(sum(weights)-1)>2e-3 or any(
                        not math.isfinite(w) or w<0 for w in weights):
                    raise RuntimeError("NONNORMALIZED_SKIN_WEIGHT:"+actor+":"+slot)
    return found


def sampled(obj, depsgraph):
    ev=obj.evaluated_get(depsgraph)
    mesh=ev.to_mesh()
    if mesh is None:raise RuntimeError("EVALUATED_MESH_MISSING")
    try:
        points=[tuple(ev.matrix_world @ v.co) for v in mesh.vertices]
        if not all(math.isfinite(z) for p in points for z in p):
            raise RuntimeError("NONFINITE_DEFORMED_VERTEX")
        mesh.calc_loop_triangles()
        faces=[tuple(t.vertices) for t in mesh.loop_triangles]
        if not faces or any(max(f)>=len(points) for f in faces):
            raise RuntimeError("EVALUATED_TRIANGLE_INVALID")
    finally:
        ev.to_mesh_clear()
    return points,faces


def skin_edges(obj):
    out=[tuple(e.vertices) for e in obj.data.edges]
    if not out:raise RuntimeError("GARMENT_EDGES_MISSING")
    # Reuse #303's bounded <=750-source-edge sample policy. All triangle
    # crossings still use full resolution, not these sampled edges.
    return out[::max(1,len(out)//750)]


HEIGHT_BINS=((0.,.60),(.60,.85),(.85,1.05),(1.05,1.25),
             (1.25,1.45),(1.45,1.80),(1.80,100.))

def height_bin(garment_height_z):
    if not math.isfinite(garment_height_z):
        raise RuntimeError("INVALID_INTERSECTION_POSITION")
    for lo,hi in HEIGHT_BINS:
        if lo<=garment_height_z<hi:return "{:.2f}-{:.2f}".format(lo,hi)
    return "OUTSIDE_SOURCE_BODY_HEIGHT"

def crossing_count(a,b):
    p,f=a; q,g=b
    ta=BVHTree.FromPolygons(p,f,all_triangles=True,epsilon=0.000001)
    tb=BVHTree.FromPolygons(q,g,all_triangles=True,epsilon=0.000001)
    pairs=sorted(set(tuple(pair) for pair in ta.overlap(tb)))
    # Use the actual *garment* triangle centroid (not a surrogate
    # body vertex) to localize confirmed triangle crossings along Blender WORLD Z.
    # This is an evidence bin, not the precise intersection coordinate.
    bins={}
    for _,garment_triangle in pairs:
        triangle=g[garment_triangle]
        height_z=sum(q[v][2] for v in triangle)/3.
        label=height_bin(height_z)
        bins[label]=bins.get(label,0)+1
    if sum(bins.values())!=len(pairs):
        raise RuntimeError("SURFACE_CROSSING_HEIGHT_HISTOGRAM_LOSS")
    return len(pairs),bins


def audit(source, out, expected_sha, frames=72):
    path=Path(source).resolve(); receipt=Path(out).resolve()
    if path==receipt or receipt.exists():
        raise RuntimeError("NO_SOURCE_OR_RECEIPT_OVERWRITE")
    raw=path.read_bytes()
    observed=hashlib.sha256(raw).hexdigest()
    if observed!=expected_sha or raw[:4]!=b"glTF":
        raise RuntimeError("SOURCE_SHA_GLTF_MISMATCH")
    if frames!=72:raise RuntimeError("FULL_72_FRAMES_REQUIRED")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objs=mesh_index()
    if len([o for o in bpy.data.objects if o.type=="ARMATURE"])!=2:
        raise RuntimeError("ACTOR_ARMATURE_COUNT_INVALID")
    result={a:{} for a in ACTORS}
    motion_samples={a:{s:[] for s in SLOTS[1:]} for a in ACTORS}
    strain={a:{s:[] for s in SLOTS[1:]} for a in ACTORS}
    frame_crossing={a:{s:[] for s in SLOTS[1:]} for a in ACTORS}
    edges={(a,s):skin_edges(objs[(a,s)]) for a in ACTORS for s in SLOTS[1:]}
    base={}
    for frame in range(1,frames+1):
        bpy.context.scene.frame_set(frame)
        dg=bpy.context.evaluated_depsgraph_get()
        for actor in ACTORS:
            body=sampled(objs[(actor,"body")],dg)
            if frame==1:
                zvals=[p[2] for p in body[0]]
                if max(zvals)<1.60 or min(zvals)>.60:
                    raise RuntimeError("BLENDER_WORLD_Z_CHARACTER_VERTICAL_AXIS_INVALID")
            for slot in SLOTS[1:]:
                garment=sampled(objs[(actor,slot)],dg)
                if frame==1:
                    values=[math.dist(garment[0][u],garment[0][v])
                            for u,v in edges[(actor,slot)]]
                    if any(z<=1e-8 for z in values):
                        raise RuntimeError("DEGENERATE_GARMENT_EDGE")
                    base[(actor,slot)]=values
                if len(garment[0])!=len(objs[(actor,slot)].data.vertices):
                    raise RuntimeError("ANIMATED_TOPOLOGY_DRIFT")
                pair_count,height_bins=crossing_count(body,garment)
                frame_crossing[actor][slot].append({
                    "frame":frame,"body_garment_surface_triangle_pairs":pair_count,
                    "height_bins_blender_world_z_m":height_bins,
                    "surface_crossing_evidence":("OBSERVED" if pair_count else
                                                 "NOT_OBSERVED_IN_THIS_FRAME"),
                })
                samples=[]
                for (u,v),rest in zip(edges[(actor,slot)],base[(actor,slot)]):
                    ratio=math.dist(garment[0][u],garment[0][v])/rest
                    if not math.isfinite(ratio):raise RuntimeError("NONFINITE_EDGE_STRAIN")
                    samples.append(abs(ratio-1.0))
                strain[actor][slot].extend(samples)
    for actor in ACTORS:
        for slot in SLOTS[1:]:
            c=frame_crossing[actor][slot]
            vals=sorted(strain[actor][slot])
            p99=vals[min(len(vals)-1,math.ceil(.99*len(vals))-1)]
            worst=max(vals)
            count=sum(row["body_garment_surface_triangle_pairs"] for row in c)
            violating=sum(1 for row in c if row["body_garment_surface_triangle_pairs"]>0)
            total_by_height={}
            for row in c:
                for key,n in row["height_bins_blender_world_z_m"].items():
                    total_by_height[key]=total_by_height.get(key,0)+n
            if sum(total_by_height.values())!=count:
                raise RuntimeError("CROSSING_HISTOGRAM_TOTAL_MISMATCH")
            result[actor][slot]={
                "crossing_height_bins_blender_world_z_m":dict(sorted(total_by_height.items())),
                "crossing_height_method":"garment_triangle_centroid_blender_world_Z; imported glTF Y-up -> Blender Z-up",
                "frames_checked":frames,
                "per_frame":c,
                "frames_with_surface_crossings":violating,
                "total_body_garment_triangle_pairs":count,
                "max_pairs_one_frame":max(row["body_garment_surface_triangle_pairs"] for row in c),
                "p99_edge_relative_strain":round(p99,6),
                "max_edge_relative_strain":round(worst,6),
                "strain_policy":"FAIL_PROXY_GT_25PCT" if p99>.25 else
                                "UNKNOWN_STRICT_BIOLOGICAL_VALIDITY",
                "surface_crossing_verdict":("FAIL_CONFIRMED_SURFACE_CROSSING"
                         if count else "UNKNOWN_NO_SURFACE_CROSSING_OBSERVED"),
                "volumetric_containment":"UNKNOWN_NOT_TESTED",
            }
    record={
        "schema":SCHEMA,"source_sha256":observed,
        "blender_version":bpy.app.version_string,
        "frame_count":frames, "actor_count":2,"rig_joints_each":35,
        "observations":result,
        "method":"full evaluated skinned triangle BVH body vs style garment, every frame",
        "edge_strain_method":"source-equivalent sampled #303 stretch proxy",
        "garment_clearance_accepted":False,
        "body_continuity_accepted":False,
        "physically_simulated_cloth":False,
        "realistic_human_facial_anatomy_accepted":False,
        "reconstructive_fit_accepted":False,
        "owner_rights_custody_merge_release_cpe_held":True,
    }
    receipt.parent.mkdir(parents=True,exist_ok=True)
    with receipt.open("x",encoding="utf8") as f:
        json.dump(record,f,sort_keys=True,indent=2)
        f.write("\n")
    print(json.dumps({"schema":SCHEMA,
                      "source_sha256":observed,
                      "frame_count":frames,
                      "summary":{a:{s:{k:result[a][s][k] for k in (
                          "frames_with_surface_crossings",
                          "total_body_garment_triangle_pairs",
                          "p99_edge_relative_strain","strain_policy",
                          "surface_crossing_verdict","crossing_height_bins_blender_world_z_m")}
                          for s in SLOTS[1:]} for a in ACTORS},
                      "garment_clearance_accepted":False},sort_keys=True))


if __name__=="__main__":
    a=sys.argv[sys.argv.index("--")+1:]
    if a==["--selftest"]:
        selftest()
    elif len(a)==3:
        audit(*a)
    else:
        raise SystemExit("usage: -- GLB RECEIPT EXPECTED_SHA, or -- --selftest")
