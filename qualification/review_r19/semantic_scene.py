#!/usr/bin/env python3
"""R19 independent Blender scene witness, public original synthetic ONLY.

Load each original .blend using bpy 4.5 in an isolated read-only runtime.
Canonicalize evaluated object geometry and transform per original frame.
Binary .blend inequality is distinct from semantic inequality.
No render, protected assets, model training, or scientific gait promotion.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import bpy

ACTORS=("CobaltOriginal","MarigoldOriginal")
def scalar(x):
 v=float(x)
 if not math.isfinite(v):raise ValueError("NONFINITE_SCENE_COORDINATE")
 return round(0.0 if abs(v)<5e-8 else v,7)
def vec(v):return [scalar(z) for z in v]
def matrix(m):return [vec(row) for row in m]
def take_mesh(obj,deps):
 observed=obj.evaluated_get(deps)
 mesh=observed.to_mesh(preserve_all_data_layers=False,depsgraph=deps)
 if mesh is None:raise ValueError("EVALUATED_MESH_UNAVAILABLE")
 try:
  return {"vertices":[vec(vertex.co) for vertex in mesh.vertices],
          "faces":[list(p.vertices) for p in mesh.polygons],
          "edges":[list(e.vertices) for e in mesh.edges]}
 finally:observed.to_mesh_clear()
def structural_scene():
 scene=bpy.context.scene
 if scene.render.fps!=12 or scene.render.fps_base!=1.0:
  raise ValueError("SOURCE_RATIONAL_CLOCK_MISMATCH")
 items=[]
 for obj in sorted(scene.objects,key=lambda o:o.name):
  value={"name":obj.name,"type":obj.type,"parent":obj.parent.name if obj.parent else None,
   "parent_type":obj.parent_type,"modifiers":[{"type":m.type,"name":m.name} for m in obj.modifiers]}
  if obj.type=="MESH":
   value["materials"]=[m.name if m else None for m in obj.data.materials]
  if obj.type=="CAMERA":
   value["camera"]={"type":obj.data.type,"lens":scalar(obj.data.lens),"clip_start":scalar(obj.data.clip_start),
     "clip_end":scalar(obj.data.clip_end)}
  if obj.type=="ARMATURE":
   value["bones"]=[{"name":b.name,"parent":b.parent.name if b.parent else None,
     "head":vec(b.head_local),"tail":vec(b.tail_local),"matrix":matrix(b.matrix_local)}
     for b in sorted(obj.data.bones,key=lambda b:b.name)]
  items.append(value)
 if not any(x["type"]=="MESH" for x in items) or sum(x["type"]=="CAMERA" for x in items)<2:
  raise ValueError("ORIGINAL_TWO_VIEW_GEOMETRY_MISSING")
 return {"render":{"fps":scene.render.fps,"fps_base":scalar(scene.render.fps_base),
   "resolution_x":scene.render.resolution_x,"resolution_y":scene.render.resolution_y},
   "frame_start":scene.frame_start,"frame_end":scene.frame_end,"objects":items}
def scene_witness():
 static=structural_scene()
 scene=bpy.context.scene
 frames=[]
 for n in range(1,25):
  scene.frame_set(n)
  deps=bpy.context.evaluated_depsgraph_get()
  objects=[]
  for obj in sorted(scene.objects,key=lambda o:o.name):
   row={"name":obj.name,"world":matrix(obj.matrix_world)}
   if obj.type=="MESH":row["evaluated_mesh"]=take_mesh(obj,deps)
   if obj.type=="ARMATURE":
    row["pose"]=[{"name":p.name,"matrix":matrix(p.matrix)} for p in sorted(obj.pose.bones,key=lambda p:p.name)]
   objects.append(row)
  frames.append({"frame":n,"objects":objects})
 return {"schema":"scp.r19.public_synthetic_blender_semantics.v1","static":static,"frames":frames}
def main():
 if len(sys.argv)!=3:raise SystemExit("expected original .blend path and output path")
 src=Path(sys.argv[1]).resolve(strict=True)
 target=Path(sys.argv[2])
 if target.exists():raise ValueError("REFUSE_OVERWRITE_FIRST_EVIDENCE")
 if src.suffix!=".blend" or src.stat().st_size>2000000:raise ValueError("SOURCE_SIZE_OR_EXTENSION_INVALID")
 bpy.ops.wm.open_mainfile(filepath=str(src),load_ui=False)
 witness=scene_witness()
 canonical=json.dumps(witness,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
 report={"schema":witness["schema"],"original_blend_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
 "scene_semantic_sha256":hashlib.sha256(canonical).hexdigest(),
 "scene_semantic_bytes":len(canonical),"objects":len(witness["static"]["objects"]),
 "frames":len(witness["frames"]),"scope":"PUBLIC_ORIGINAL_SYNTHETIC_ONLY",
 "biomechanics":"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM",
 "human_behavior":"FAIL_ABSTRACT_LIMBS_ONLY","product":"HELD_R009_NOT_RUN_NOT_ADMITTED"}
 target.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
 print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
