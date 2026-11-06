#!/usr/bin/env python3
"""Native Blender evaluated triangle-surface BVH contact witness.

Compares *actual* skinned triangles using Blender BVHTree at all 72 keyed
motion frames per state, alongside the independent 72-frame vertex proxy.
Surface-overlap counts can mean touch OR crossing. Fully contained surfaces
and near misses are not detected. Does not grant collision or cloth acceptance.
Public source-original characters ONLY. No private identities or assets.
"""
import hashlib
import json
import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCHEMA = "scp.r009.original_bvh_surface_contact.v2"
ACTORS = ("AsterOriginal", "JuniperOriginal")
SLOTS = ("top", "bottom", "footwear")
FRAMES = tuple(range(0, 143, 2))

def _bvh_from_evaluated_object(obj, depsgraph):
    eval_ob = obj.evaluated_get(depsgraph)
    mesh = eval_ob.to_mesh()
    try:
        if mesh is None or not mesh.vertices or not mesh.polygons:
            raise ValueError("INVALID_EVALUATED_MESH:" + obj.name)
        matrix = eval_ob.matrix_world
        verts = [matrix @ v.co for v in mesh.vertices]
        # All original glTF primitives are triangulated. loop_triangles is the
        # tessellated view of Blender's imported/evaluated mesh.
        mesh.calc_loop_triangles()
        tris = [tuple(int(k) for k in tri.vertices) for tri in mesh.loop_triangles]
        if not tris or any(len(t) != 3 or any(i < 0 or i >= len(verts) for i in t)
                           for t in tris):
            raise ValueError("INVALID_TRIANGLE_INDEX")
        if any(not math.isfinite(c) for p in verts for c in p):
            raise ValueError("NONFINITE_VERTEX")
        return BVHTree.FromPolygons(verts, tris, all_triangles=True, epsilon=.0001), len(tris)
    finally:
        eval_ob.to_mesh_clear()

def calibration():
    """Falsify gross BVH misuse with known intersecting / separated surfaces."""
    a = BVHTree.FromPolygons(
        [Vector((-1.,-1.,0.)),Vector((1.,-1.,0.)),Vector((0.,1.,0.))],
        [(0,1,2)], all_triangles=True, epsilon=0.)
    b = BVHTree.FromPolygons(
        [Vector((0.,-.6,-1.)),Vector((0.,.6,-1.)),Vector((0.,0.,1.))],
        [(0,1,2)], all_triangles=True, epsilon=0.)
    distant = BVHTree.FromPolygons(
        [Vector((0.,-.6,4.)),Vector((0.,.6,4.)),Vector((0.,0.,5.))],
        [(0,1,2)], all_triangles=True, epsilon=0.)
    if not a.overlap(b):
        raise ValueError("BVH_POSITIVE_INTERSECTION_CALIBRATION_FAILED")
    if a.overlap(distant):
        raise ValueError("BVH_NEGATIVE_SEPARATION_CALIBRATION_FAILED")
    return True

def inspect(scene, model_sha256):
    if not (isinstance(model_sha256,str) and len(model_sha256)==64
            and all(c in "0123456789abcdef" for c in model_sha256)):
        raise ValueError("INVALID_SOURCE_SHA256")
    calibration()
    objects = {o.name:o for o in bpy.data.objects if o.type=="MESH"}
    observations = {actor: {s:[] for s in SLOTS} for actor in ACTORS}
    for actor in ACTORS:
        for name in ("body",)+SLOTS:
            if actor+"_Wardrobe_"+name not in objects:
                raise ValueError("REQUIRED_ORIGINAL_SOURCE_MESH_MISSING:"+actor+"_"+name)
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        for actor in ACTORS:
            body_tree, body_tris = _bvh_from_evaluated_object(
                objects[actor+"_Wardrobe_body"], deps)
            for slot in SLOTS:
                garment_tree, garment_tris = _bvh_from_evaluated_object(
                    objects[actor+"_Wardrobe_"+slot], deps)
                # Native BVH.overlap returns exact paired triangle indices in
                # this sampled evaluated mesh, not vertex proximity estimates.
                contacts = body_tree.overlap(garment_tree)
                sample = {
                    "frame":frame, "body_triangles":body_tris,
                    "garment_triangles":garment_tris,
                    "surface_overlap_triangle_pairs":len(contacts),
                    "sample_overlap_pairs":[[int(i),int(j)] for i,j in contacts[:8]],
                    "contact_or_crossing_not_disambiguated":True,
                    "closed_volume_containment_detected":False,
                    "collision_free_proven":False,
                    "fit_accepted":False
                }
                observations[actor][slot].append(sample)
    by_actor={}
    for actor in ACTORS:
        by_actor[actor]={}
        for slot in SLOTS:
            rows=observations[actor][slot]
            by_actor[actor][slot]={
                "sample_count":len(rows),
                "frames_with_surface_overlaps":sum(
                    r["surface_overlap_triangle_pairs"]>0 for r in rows),
                "max_pair_count":max(r["surface_overlap_triangle_pairs"] for r in rows),
                "pairs_total":sum(r["surface_overlap_triangle_pairs"] for r in rows),
                "samples":rows}
    return {"schema":SCHEMA, "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "source_sha256":model_sha256,"actor_count":len(ACTORS),
            "motion_frames_evaluated":len(FRAMES),
            "frame_indices":list(FRAMES),"slots":list(SLOTS),
            "native_bvh_positive_negative_calibration":True,
            "method":"BLENDER_EVALUATED_SKINNED_TRIANGLE_BVH_OVERLAP",
            "per_actor_slot":by_actor,
            "all_72_motion_frames_evaluated_for_bvh":True,
            "all_72_motion_frames_evaluated_for_vertex_proxy":True,
            "no_overlap_is_not_no_intersection_proof_between_samples":True,
            "fully_qualified_frame_interpolation":False,
            "contact_and_penetration_sign_independent":False,
            "no_contact_is_not_no_containment_proof":True,
            "surface_tear_or_holes_qualified":False,
            "collision_free_proven":False,
            "garment_fit_accepted":False,
            "human_visual_accepted":False,
            "release_approved":False}
