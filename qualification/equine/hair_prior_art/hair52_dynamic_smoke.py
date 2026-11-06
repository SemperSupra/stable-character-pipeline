#!/usr/bin/env python3
"""Synthetic 48-frame Blender 5.2.3 hair-node dynamics experiment.

Tests ACTUAL evaluated geometry, distinguishes source rigid follow from
secondary motion. Experimental failure is scientific/ABI evidence, never
reason to re-pin production 4.5.15 or to claim a simulation succeeded.
"""
import bpy
import hashlib
import json
import math
import resource
import sys
import time
from pathlib import Path
from mathutils import Vector

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=1:
    raise SystemExit("usage: blender -b --python hair52_dynamic_smoke.py -- <receipt.json>")
out=Path(sys.argv[sys.argv.index("--")+1])
if out.exists():raise ValueError("would overwrite an earlier source experiment")
out.parent.mkdir(parents=True,exist_ok=True)
receipt={
    "schema":"equine.blender52.dynamic.original_synthetic.v1",
    "blender":bpy.app.version_string,
    "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "scene":"tiny original synthetic scalp plus THREE guide curves",
    "frames_requested":48,
    "physics_status":"EXPERIMENTAL_UNVERIFIED",
    "motion_measured":False,
    "visual_collision_quality":"UNKNOWN",
    "source_and_release_hold":"KEEP",
    "production_blender_4_5_15_untouched":True,
    "samples":[],
    "errors":[],
}
started=time.perf_counter()
stage="initialize"
try:
    if bpy.app.version[:3]!=(5,2,3):raise ValueError("exact version mismatch")
    stage="create synthetic source and hair"
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=12,radius=.5)
    surface=bpy.context.object;surface.name="SyntheticScalpMover"
    bpy.ops.object.curves_empty_hair_add()
    hair=bpy.context.object
    if hair is None or hair.type!="CURVES":raise ValueError("hair object not created")
    data=hair.data
    stage="create three six-point guide curves"
    data.add_curves([6,6,6])
    if len(data.curves)!=3 or len(data.points)!=18:
        raise ValueError("source curve cardinality")
    for j,offset in enumerate((-.045,0.,.045)):
        for k in range(6):
            i=j*6+k
            z=math.sqrt(.5**2-offset**2)
            data.points[i].position=(offset,0.,z+k*.06)
            data.points[i].radius=.002*(1.-.8*k/5)
    data.update_tag()
    stage="inspect hair dynamics modifiers"
    mods=[m for m in hair.modifiers if m.type=="NODES"]
    physics=[m for m in mods if "Hair Dynamics" in m.name]
    if len(physics)!=1 or not physics[0].node_group:
        raise ValueError("built-in Hair Dynamics group not attached")
    modifier=physics[0]
    input_interfaces=[]
    for item in modifier.node_group.interface.items_tree:
        if item.item_type=="SOCKET" and item.in_out=="INPUT":
            input_interfaces.append({"name":item.name,"id":item.identifier,
                "socket_type":item.socket_type,"default_repr":repr(getattr(item,"default_value","UNAVAILABLE"))[:120]})
            if item.name.strip().lower()=="mode":
                try:
                    # For experimental GN menu values, 1 requests Physics
                    # after default Animation=0. Read back to prevent fake API
                    # configuration success; scientific results still observed.
                    modifier[item.identifier]=1
                except Exception as e:
                    receipt["errors"].append("physics_mode_control:"+str(e)[:160])
    stage="motion setup"
    receipt["modifier_inputs"]=input_interfaces
    if not any(item["name"].lower()=="mode" for item in input_interfaces):
        raise ValueError("no motion mode interface; experimental ABI unknown")
    scene=bpy.context.scene
    scene.frame_start=1;scene.frame_end=48;scene.render.fps=24
    for frame,x in ((1,0.),(16,.18),(32,-.10),(48,0.)):
        surface.location.x=x
        surface.keyframe_insert(data_path="location",index=0,frame=frame)
    stage="evaluate actual frames"
    evaluated=[]
    for frame in range(1,49):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get()
        obj=hair.evaluated_get(deps)
        if obj.type!="CURVES" or len(obj.data.points)!=18:
            raise ValueError("evaluated source curve points lost at frame "+str(frame))
        mat=obj.matrix_world
        a=[tuple(mat@obj.data.points[j*6].position) for j in range(3)]
        b=[tuple(mat@obj.data.points[j*6+5].position) for j in range(3)]
        p=[tuple(b[j][k]-a[j][k] for k in range(3)) for j in range(3)]
        if any(not math.isfinite(v) for row in p for v in row):
            raise ValueError("nonfinite native evaluated hair")
        evaluated.append({"frame":frame,"root_world_m":a,"tip_world_m":b,
                          "tip_minus_root_m":p,"scalp_world_x_m":surface.location.x})
    receipt["samples"]=evaluated
    dist=lambda a,b:math.sqrt(sum((a[k]-b[k])**2 for k in range(3)))
    # Require displacement relative to the moving root. Rig-follow alone is
    # NOT simulated hair and must not qualify as dynamic secondary motion.
    max_shape_delta=max(dist(row["tip_minus_root_m"][i],
                             evaluated[0]["tip_minus_root_m"][i])
                        for row in evaluated for i in range(3))
    max_root_err=max(abs(row["root_world_m"][i][0]-
                         (row["scalp_world_x_m"]+(-.045,0.,.045)[i]))
                     for row in evaluated for i in range(3))
    receipt["max_relative_hair_tip_motion_m"]=max_shape_delta
    receipt["max_root_x_error_m"]=max_root_err
    receipt["frame_count"]=len(evaluated)
    if max_root_err>.04:
        receipt["errors"].append("animated_follicle_root_lost")
    if max_shape_delta<.002:
        receipt["errors"].append("no_independent_secondary_hair_motion_detected")
    receipt["motion_measured"]=max_shape_delta>=.002 and max_root_err<=.04
    receipt["physics_status"]="EVALUATED_SECONDARY_MOTION_OBSERVED_UNCALIBRATED" if receipt["motion_measured"] else "NO_QUALIFIED_HAIR_MOTION"
except Exception as e:
    import traceback
    receipt["errors"].append(stage+":"+type(e).__name__+":"+str(e)[:350])
    receipt["first_traceback"]=traceback.format_exc(limit=5)[:1400]
receipt["wall_seconds"]=round(time.perf_counter()-started,3)
receipt["maxrss_linux_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
receipt["verdict"]="EXPERIMENTAL_48F_MOTION_OBSERVED_NOT_SCIENTIFIC_ACCEPTANCE" if not receipt["errors"] and receipt["motion_measured"] else "EXPERIMENTAL_MOTION_FAIL_CLOSED"
out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("BLENDER52_48F_HAIR_MOTION",json.dumps({k:receipt.get(k) for k in ("verdict","physics_status","max_relative_hair_tip_motion_m","max_root_x_error_m","wall_seconds","errors")},sort_keys=True))
if receipt["errors"]:raise RuntimeError("; ".join(receipt["errors"]))
