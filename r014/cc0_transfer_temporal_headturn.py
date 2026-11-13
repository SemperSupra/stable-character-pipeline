"""R014 corrected CC0 attachments: actual source-native head-turn temporal fit trial.

Real Blender armature motion, packed source geometry, per-frame independent
evaluated-body BVH and accessory sampling, stills and H.264. Does not assert
clinical contact, full motion readiness or cinematic photorealism.
"""
import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def sha(path):
    h=sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def parse():
    p=argparse.ArgumentParser()
    p.add_argument("--sex",choices=("female","male"),required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--receipt",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def evmesh(obj,dep):
    ev=obj.evaluated_get(dep)
    m=ev.to_mesh()
    try:
        coords=[ev.matrix_world@v.co for v in m.vertices]
        faces=[tuple(int(i) for i in p.vertices) for p in m.polygons]
        return coords,faces
    finally:ev.to_mesh_clear()

def sample_indices(n,maxn=256):
    count=min(n,maxn)
    return sorted({int(round(i*(n-1)/max(count-1,1))) for i in range(count)})

def inventory(rig,body,sex):
    objs=[]
    for o in sorted(bpy.data.objects,key=lambda x:x.name):
        if o.type!="MESH" or o==body:continue
        if o.name.startswith("R014_"+sex+"_") or o.parent==rig or o.parent==body:
            objs.append(o)
    assert len(objs)>=6,"REQUIRES_ORIGINAL_NATIVE_ACCESSORIES"
    return objs

def sample_frame(scene,frame,body,assets):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    dep=bpy.context.evaluated_depsgraph_get()
    body_verts,body_faces=evmesh(body,dep)
    assert len(body_verts)>=10000 and len(body_faces)>=10000
    tree=BVHTree.FromPolygons(body_verts,body_faces,all_triangles=False,epsilon=1e-7)
    sampled={}
    for obj in assets:
        verts,faces=evmesh(obj,dep)
        if not verts:continue
        idx=sample_indices(len(verts))
        pts=[verts[i] for i in idx]
        dist=[]
        sides=[]
        for point in pts:
            near=tree.find_nearest(point)
            if near[0] is not None:
                closest,normal,_,d=near
                dist.append(float(d))
                sides.append(float((point-closest).dot(normal)))
        assert len(dist)==len(pts),("MISSING_PROXIMITY_POINT",obj.name)
        sampled[obj.name]={
            "points":[[float(v) for v in p] for p in pts],
            "evaluated_vertex_count":len(verts),
            "samples":len(pts),
            "mean_nearest_body_native":float(sum(dist)/len(dist)),
            "max_nearest_body_native":max(dist),
            "normal_side_negative_fraction_provisional":sum(v<0 for v in sides)/len(sides),
        }
    return {
        "frame":frame,
        "body_points":[[float(v) for v in body_verts[i]] for i in sample_indices(len(body_verts),1024)],
        "body_world_z_span":max(float(v.z) for v in body_verts)-min(float(v.z) for v in body_verts),
        "accessories":sampled
    }

def pmax(a,b):
    assert len(a)==len(b)
    return max(math.dist(x,y) for x,y in zip(a,b)) if a else 0

def head_bone(rig):
    candidates=[bone.name for bone in rig.pose.bones if "head" in bone.name.lower() and not any(
         end in bone.name.lower() for end in ["_end","end","nub","helper","target"])]
    if not candidates:
        return None,[]
    # Prefer the actual named head control over eye attachments and endpoint.
    names=sorted(candidates,key=lambda name:(name.lower()!="head",len(name),name))
    return rig.pose.bones[names[0]],names

def glb_meta(path):
    with path.open("rb") as f:
        magic,version,length=struct.unpack("<4sII",f.read(12))
        assert magic==b"glTF" and version==2 and length==path.stat().st_size
        n,kind=struct.unpack("<I4s",f.read(8))
        assert kind==b"JSON"
        doc=json.loads(f.read(n))
    rot=sum(c.get("target",{}).get("path")=="rotation" for a in doc.get("animations",[]) for c in a.get("channels",[]))
    return {"sha256":sha(path),"bytes":path.stat().st_size,
            "mesh_count":len(doc.get("meshes",[])),
            "skins":len(doc.get("skins",[])),
            "animations":len(doc.get("animations",[])),
            "rotation_channels":rot}

def main():
    a=parse();a.out.mkdir(parents=True,exist_ok=True)
    assert Path(bpy.data.filepath).resolve()==a.source.resolve()
    src=json.loads(a.receipt.read_text())
    assert src["sex_macro"]==a.sex
    assert src["status"]=="PASS_EXPERIMENTAL_NATIVE_MESH_TRANSFER_AND_REVIEW_FILES_ONLY"
    assert src["native_blend"]["sha256"]==sha(a.source)
    scene=bpy.context.scene
    rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
    body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
    assert rig.type=="ARMATURE" and body.type=="MESH"
    assert len(rig.data.bones)==163 and len(body.data.vertices)==19158
    assets=inventory(rig,body,a.sex)
    head,candidates=head_bone(rig)
    # Always preserve source 1/8/16 limbs; add head movement only if native
    # source has a plausible head control. Missing is evidence, not fabricated.
    if head:
        head.rotation_mode="XYZ"
        for frame,angle in ((1,0.0),(8,0.24),(16,0.0)):
            head.rotation_euler=(0.0,angle,0.0)
            head.keyframe_insert(data_path="rotation_euler",frame=frame)
    frames=[sample_frame(scene,f,body,assets) for f in (1,8,16)]
    first,mid,last=frames
    core_motion=pmax(first["body_points"],mid["body_points"])
    core_rest=pmax(first["body_points"],last["body_points"])
    actor=[]
    for name in sorted(set(first["accessories"]) & set(mid["accessories"]) & set(last["accessories"])):
        orig=first["accessories"][name];posed=mid["accessories"][name];recovered=last["accessories"][name]
        actor.append({
          "name":name,"samples":orig["samples"],
          "rest_mean_body_gap_native":round(orig["mean_nearest_body_native"],8),
          "head_turn_mean_body_gap_native":round(posed["mean_nearest_body_native"],8),
          "frame16_mean_body_gap_native":round(recovered["mean_nearest_body_native"],8),
          "gap_drift_abs_mean_native":round(abs(posed["mean_nearest_body_native"]-orig["mean_nearest_body_native"]),8),
          "actual_vertex_motion_max_native":round(pmax(orig["points"],posed["points"]),8),
          "restored_vertex_delta_native":round(pmax(orig["points"],recovered["points"]),8),
          "normal_side_negative_fraction_provisional":round(posed["normal_side_negative_fraction_provisional"],6),
          "triangulated_watertight_collision_test":"NOT_RUN"
        })
    assert len(actor)>=6
    report={
      "schema":"r014.cc0.actual_head_turn_and_accessory_fit_temporal.v1",
      "status":"PASS_BOUNDED_REAL_SOURCE_NATIVE_TEMPORAL_EVIDENCE_CAPTURE_ONLY",
      "sex_macro":a.sex,"source":a.source.name,"source_sha256":sha(a.source),
      "official_source":"MPFB 6ff1eb358f6c1959ced77e79e6dd2406d9a71f49 with CC0 MAKESKIN assets",
      "rig_bones":len(rig.data.bones),"source_body_vertices":len(body.data.vertices),
      "source_actual_accessories":len(actor),
      "head_control_candidates":candidates,
      "selected_head_control":head.name if head else None,
      "controlled_local_head_rotation_y_rad":0.24 if head else None,
      "head_actuation_status":"ACTUATED_SOURCE_HEAD_BONE" if head else "UNKNOWN_NO_SOURCE_HEAD_BONE",
      "native_body_motion_max":round(core_motion,8),
      "native_body_return_max":round(core_rest,8),
      "body_geometry_motion_condition":core_motion>0.001,
      "body_geometry_restoration_condition":core_rest<=0.0001,
      "per_asset_temporal":actor,
      "source_frames":[1,8,16],
      "material_uv_qualified":"SEPARATE_INDEPENDENT_BATCH",
      "facial_anatomy_contact":"HOLD_NO_WATERTIGHT_OR_CLINICAL_TEST",
      "cinematic_photoreal":"HOLD",
      "merge_release":"HOLD",
      "limits":["The upperbody/dynamic head source rig may not move every accessory",
                "Closest surface distances are unsigned and not collision/inside-outside proof",
                "No true eyes blinking, tongue visemes, tissue physics, cloth/hair simulation",
                "No user likeness, no CPE semantic recognition or generation-eligibility decisions",
                "Actual human anatomical units and motion contact not calibrated"]
    }
    # A real gap/unchanged asset is a diagnosed negative, not a swallowed PASS.
    stationary=[x["name"] for x in actor if x["actual_vertex_motion_max_native"]<0.00005]
    report["stationary_actual_accessories_under_head_turn"]=stationary
    if not head or not report["body_geometry_motion_condition"] or not report["body_geometry_restoration_condition"]:
        report["head_turn_fit_status"]="FAIL_OR_UNQUALIFIED_ACTUATION"
    elif stationary:
        report["head_turn_fit_status"]="HOLD_ACCESSORY_NOT_ALL_MOVING"
    else:
        report["head_turn_fit_status"]="HOLD_SURFACE_CONTACT_UNQUALIFIED"
    scene.frame_set(1)
    scene.frame_start=1;scene.frame_end=16;scene.render.fps=12
    # Save native source *after* adding head-actuation to preserve its real
    # motion curves. Never change or overwrite the upstream corrected scene.
    native=a.out/("R014_"+a.sex+"_head_turn_source_native_research.blend")
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    report["native_scene"]={"filename":native.name,"sha256":sha(native),"bytes":native.stat().st_size}
    # Portable animated skinned asset, not a static mesh/film proxy.
    bpy.ops.object.select_all(action="DESELECT")
    selections=[body,rig]+assets
    for obj in selections:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    glb=a.out/("R014_"+a.sex+"_head_turn_skin_and_accessories.glb")
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",
             use_selection=True,export_animations=True,export_morph=True,
             export_skins=True,export_yup=True)
    report["glb"]=glb_meta(glb)
    if not (report["glb"]["skins"]>=1 and report["glb"]["animations"]>=1 and report["glb"]["rotation_channels"]>=2):
        raise RuntimeError("EXPORT_LACKS_SKINNED_ANIMATED_GLTF")
    scene.render.engine="CYCLES";scene.cycles.device="CPU";scene.cycles.samples=8
    scene.render.threads_mode="FIXED";scene.render.threads=4
    scene.render.resolution_x=384;scene.render.resolution_y=500
    scene.render.image_settings.file_format="PNG"
    for label,frame in (("rest",1),("turn",8)):
        scene.frame_set(frame)
        image=a.out/(a.sex+"_head_turn_"+label+".png")
        scene.render.filepath=str(image)
        bpy.ops.render.render(write_still=True)
        assert image.stat().st_size>3000
        report.setdefault("source_stills",[]).append({"name":image.name,"sha256":sha(image)})
    scene.render.resolution_x=256;scene.render.resolution_y=330
    scene.render.image_settings.file_format="FFMPEG"
    scene.render.ffmpeg.format="MPEG4";scene.render.ffmpeg.codec="H264"
    scene.render.ffmpeg.ffmpeg_preset="GOOD"
    prefix="R014_"+a.sex+"_head_turn_actual_16frame"
    scene.render.filepath=str(a.out/(prefix+".mp4"))
    bpy.ops.render.render(animation=True)
    films=list(a.out.glob(prefix+"*.mp4"))
    assert len(films)==1 and films[0].stat().st_size>512
    result=subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
       "-show_entries","stream=codec_name,width,height,nb_frames",
       "-show_entries","format=duration","-of","json",str(films[0])],
       capture_output=True,text=True,check=True,timeout=30)
    movie=json.loads(result.stdout)
    v=movie["streams"][0]
    assert v["codec_name"]=="h264" and int(v["nb_frames"])==16
    report["movie"]={"name":films[0].name,"bytes":films[0].stat().st_size,
                     "sha256":sha(films[0]),"ffprobe":movie}
    (a.out/"temporal_fit_receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("R014_ACTUAL_HEAD_TURN_TEMPORAL",json.dumps({
      "status":report["status"],"fit_status":report["head_turn_fit_status"],
      "sex":a.sex,"source_head_bone":report["selected_head_control"],
      "source_actor_assets":len(actor),"stationary":stationary,
      "body_motion":report["native_body_motion_max"],
      "body_rest_error":report["native_body_return_max"],
      "glb":report["glb"]},sort_keys=True))
if __name__=="__main__":main()
