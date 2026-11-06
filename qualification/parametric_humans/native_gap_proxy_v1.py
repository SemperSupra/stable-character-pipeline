#!/usr/bin/env python3
"""Run inside Blender with an already imported original-only R009 GLB.

Measure source-original geometry proximity across 72 motion frames. These
nearest-VERTEX distances intentionally do not estimate interpenetration
and cannot qualify garments, collision dynamics or realistic skinning.
"""
from __future__ import annotations
import bpy
from mathutils.kdtree import KDTree
from gap_metrics_v1 import SCHEMA,summarize

ACTORS=("AsterOriginal","JuniperOriginal")
GARMENTS=("top","bottom","footwear")
FRAMES=tuple(range(0,143,2))

def _sample_world_positions(obj,depgraph,limit):
    evaluated=obj.evaluated_get(depgraph)
    mesh=evaluated.to_mesh()
    try:
        if mesh is None or not mesh.vertices:
            raise ValueError("EMPTY_EVALUATED_GEOMETRY:"+obj.name)
        transform=evaluated.matrix_world
        step=max(1,len(mesh.vertices)//limit)
        return [transform@mesh.vertices[i].co
                for i in range(0,len(mesh.vertices),step)][:limit]
    finally:
        evaluated.to_mesh_clear()

def _body_index(body,depgraph):
    # Exactly evaluated source-original skinned vertex geometry.
    evaluated=body.evaluated_get(depgraph)
    mesh=evaluated.to_mesh()
    try:
        if mesh is None or not mesh.vertices:
            raise ValueError("BODY_EVALUATED_GEOMETRY_MISSING")
        tree=KDTree(len(mesh.vertices))
        matrix=evaluated.matrix_world
        for i,v in enumerate(mesh.vertices):
            tree.insert(matrix@v.co,i)
        tree.balance()
        return tree,len(mesh.vertices)
    finally:
        evaluated.to_mesh_clear()

def measure_scene(scene):
    objects={obj.name:obj for obj in bpy.data.objects}
    grouped={}
    for actor in ACTORS:
        body_name=actor+"_Wardrobe_body"
        if body_name not in objects:
            raise ValueError("SOURCE_BODY_MESH_MISSING:"+actor)
        for garment in GARMENTS:
            if actor+"_Wardrobe_"+garment not in objects:
                raise ValueError("SOURCE_GARMENT_MISSING:"+actor+":"+garment)
        grouped[actor]={g:[] for g in GARMENTS}
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get()
        for actor in ACTORS:
            kd,body_count=_body_index(objects[actor+"_Wardrobe_body"],deps)
            for slot in GARMENTS:
                pos=_sample_world_positions(objects[actor+"_Wardrobe_"+slot],deps,limit=180)
                distances=[kd.find(v)[2] for v in pos]
                row={"frame":frame,"evaluated_body_vertices":body_count,
                     **summarize(distances)}
                grouped[actor][slot].append(row)
    return {"schema":SCHEMA,"actor_count":len(ACTORS),
            "motion_frames_evaluated":len(FRAMES),
            "frame_indices":list(FRAMES),
            "garment_categories":list(GARMENTS),
            "per_actor_garment":grouped,
            "source_original_only":True,
            "basis":"source-original evaluated glTF skinning, Blender 4.5",
            "metric":"VERTEX_TO_NEAREST_BODY_VERTEX_PROXY",
            "per_frame_exhaustive_geometry":False,
            "body_self_intersection_checked":False,
            "garment_triangle_intersection_checked":False,
            "garment_fit_accepted":False,
            "collision_qualified":False,
            "anatomical_qualified":False,
            "release_approved":False}
