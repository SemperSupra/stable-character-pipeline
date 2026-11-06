#!/usr/bin/env python3
"""Isolated 5.2.3 experimental *source-driven proxy* hair physics.

Each of 6 real original 30-joint pony root/tip trajectories is attached to a
small separately animated synthetic spherical emitter. This is an INTEROP
step, not an original pony body/collision/visual simulation. No production
.blend mutation, no source ownership/rights assumptions, no model export.
"""
import bpy
import hashlib
import json
import math
import os
import resource
import sys
import time
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pony_source_trajectory import classify,distance

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=2:
    raise SystemExit("usage: blender -b --python pony52_source_shadow.py -- <source_48f.json> <output.json>")
src,out=map(Path,sys.argv[sys.argv.index("--")+1:])
if not src.is_file() or out.exists():
    raise ValueError("source capsule missing or output already exists")
if not 1000 < src.stat().st_size < 2000000:
    raise ValueError("source capsule size invalid")
out.parent.mkdir(parents=True,exist_ok=True)
mode=os.environ.get("SCP_52_MODE","physics")
if mode not in ("physics","animation"):
    raise ValueError("invalid experimental solver control mode")
started=time.perf_counter()
raw=src.read_bytes()
capsule=json.loads(raw)
source_validation=classify(capsule)
result={"schema":"equine.pony.xpbd_source_proxy_48f.v1",
        "source_capsule_sha256":source_validation["source_capsule_sha256"],
        "source_blend_sha256":capsule["source_blend_sha256"],
        "source_rig":"PonyRig30","source_cards_total":1050,
        "mode":mode,"backend":"Blender 5.2.3 Hair Dynamics",
        "shadow_geometry":"six original skin-driven guide roots/tips on isolated synthetic emitter proxies",
        "not_original_body_collision":True,
        "production_blender_4_5_15_untouched":True,
        "science_hold":"KEEP","release_admission":False,
        "frames":[],"errors":[]}
stage="initialization"
try:
    if bpy.app.version[:3]!=(5,2,3):
        raise ValueError("binary Blender exact release mismatch")
    scene=bpy.context.scene
    scene.frame_start=1
    scene.frame_end=48
    scene.render.fps=24
    actors=[]
    for record in capsule["guides"]:
        card=record["card_id"];region=record["region"]
        samples=record["samples"]
        origin=Vector(samples[0]["root_m"])
        resttip=Vector(samples[0]["tip_m"])
        span=resttip-origin
        if not .02<span.length<1.0:
            raise ValueError("source hair rest length invalid")
        stage="create original-source emitter_"+str(card)
        # Create a tiny proxy source surface around the ACTUAL follicle
        # in rest coordinates. It moves with the source rig trajectory.
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=.05)
        surface=bpy.context.object
        surface.name="SourceFollicleEmitter_"+str(card)
        center=origin-Vector((0.,0.,.05))
        for vert in surface.data.vertices:
            vert.co+=center
        surface.data.update()
        bpy.ops.object.curves_empty_hair_add()
        hair=bpy.context.object
        if hair is None or hair.type!="CURVES":
            raise ValueError("native hair CURVES operator missing")
        hair.name="SourceDrivenHair_"+str(card)
        data=hair.data
        data.add_curves([6])
        for j in range(6):
            t=j/5.
            data.points[j].position=origin+span*t
            data.points[j].radius=.002*(1.-.8*t)
        data.update_tag()
        dynamics=[m for m in hair.modifiers if m.type=="NODES" and "Hair Dynamics" in m.name]
        if len(dynamics)!=1 or dynamics[0].node_group is None:
            raise ValueError("source root hair physics node missing")
        original=dynamics[0]
        private=original.node_group.copy()
        private.name="ShetlandShadowSource_"+str(card)+"_"+mode
        socket=[x for x in private.interface.items_tree
                if x.item_type=="SOCKET" and x.in_out=="INPUT" and x.name.strip().lower()=="mode"]
        if len(socket)!=1:
            raise ValueError("experimental menu socket absent or duplicated")
        expected="Physics (Experimental)" if mode=="physics" else "Animation"
        socket[0].default_value=expected
        if socket[0].default_value!=expected:
            raise ValueError("experimental mode writeback false")
        hair.modifiers.remove(original)
        native=hair.modifiers.new(name="EquineSourceShadow_"+mode,type="NODES")
        native.node_group=private
        # The source capsule, not a guessed sinusoid, drives each emitter.
        for item in samples:
            motion=Vector(item["root_m"])-origin
            surface.location=motion
            surface.keyframe_insert(data_path="location",frame=item["frame"])
        actors.append((card,region,hair,origin,samples))
    stage="evaluate_real_source_motion"
    for frame in range(1,49):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get()
        row={"frame":frame,"samples":[]}
        for card,region,hair,origin,samples in actors:
            evaluated=hair.evaluated_get(deps)
            if evaluated.type!="CURVES" or len(evaluated.data.points)!=6:
                raise ValueError("source guide points missing at frame "+str(frame))
            world=evaluated.matrix_world.copy()
            root=world@evaluated.data.points[0].position
            tip=world@evaluated.data.points[5].position
            target=Vector(samples[frame-1]["root_m"])
            delta=tip-root
            if any(not math.isfinite(float(x)) for x in (root.x,root.y,root.z,tip.x,tip.y,tip.z)):
                raise ValueError("evaluated source guide nonfinite")
            row["samples"].append({"card_id":card,"region":region,
                   "root_world_m":[float(x) for x in root],
                   "tip_world_m":[float(x) for x in tip],
                   "source_root_m":[float(x) for x in target],
                   "tip_minus_root_m":[float(x) for x in delta],
                   "source_skin_root_error_m":float((root-target).length)})
        result["frames"].append(row)
    result["max_source_root_error_m"]=max(x["source_skin_root_error_m"]
        for row in result["frames"] for x in row["samples"])
    result["guide_count"]=len(actors)
    result["frame_count"]=len(result["frames"])
    # We intentionally do NOT demand source realism/physics approval here.
    # A nonzero deformation in Physics must be compared with the *same*
    # source's rigid Animation control in the independent receipt oracle.
    if result["max_source_root_error_m"]>.02:
        result["errors"].append("lost_source_follicle_attachment")
except Exception as e:
    import traceback
    result["errors"].append(stage+":"+type(e).__name__+":"+str(e)[:280])
    result["first_traceback"]=traceback.format_exc(limit=6)[:1200]
result["runtime_seconds"]=round(time.perf_counter()-started,4)
result["maxrss_linux_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
result["status"]="SOURCE_48F_PROXY_GEOMETRY_MEASURED_NO_SCIENCE" if not result["errors"] else "SOURCE_PROXY_FAIL_CLOSED"
out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
print("PONY30J_NATIVE_52_SOURCE_SHADOW",json.dumps({k:result.get(k) for k in ("status","mode","guide_count","frame_count","max_source_root_error_m","runtime_seconds","errors")},sort_keys=True))
if result["errors"]:
    raise RuntimeError("; ".join(result["errors"]))
