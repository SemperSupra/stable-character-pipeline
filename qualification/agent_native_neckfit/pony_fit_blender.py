#!/usr/bin/env python3
"""Candidate-only, source-original 26-bone pony inverse-rendering A/B experiment.

Genuine native Blender renders at two source-pinned camera poses and two source
animation frames. Reference is synthetic SELF-RENDER, not a real pony photo.
No pretrained model, actor LLM, protected data, or source-asset modification.
"""
import bpy
import hashlib
import json
import sys
from pathlib import Path
from mathutils import Vector

if "--" not in sys.argv:
    raise SystemExit("usage: blender --python pony_fit_blender.py -- original.blend output_directory")
args=sys.argv[sys.argv.index("--")+1:]
if len(args)!=2: raise SystemExit("exactly two arguments required")
source=Path(args[0]).resolve(strict=True)
out=Path(args[1]).resolve()
out.mkdir(parents=True,exist_ok=True)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

bpy.ops.wm.open_mainfile(filepath=str(source))
sc=bpy.context.scene
rig=bpy.data.objects.get("PonyRig26")
assert rig and rig.type=="ARMATURE"
assert len(rig.data.bones)==26,len(rig.data.bones)
neck=rig.pose.bones.get("neck")
assert neck and neck.rotation_mode=="XYZ"
for obj in sc.objects:
    if obj.type=="MESH" and obj.name=="ground": obj.hide_render=True
cam=sc.camera
assert cam and cam.type=="CAMERA"
cam.data.type="ORTHO"
cam.data.ortho_scale=2.45
sc.render.engine="CYCLES"
sc.cycles.samples=4
sc.cycles.use_denoising=False
sc.render.film_transparent=True
sc.render.resolution_x=256
sc.render.resolution_y=256
sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG"
sc.render.image_settings.color_mode="RGBA"
sc.render.image_settings.color_depth="8"
sc.render.image_settings.compression=40

cameras={
 "side":(0.25,-3.2,1.22),
 "oblique":(2.3,-2.8,1.33)
}
frames=[12,24]
angles=[-0.6,0.0,0.6]
rows=[]
source_sha=sha(source)
for frame in frames:
  sc.frame_set(frame)
  source_angle=neck.rotation_euler.z
  for cname,cpos in cameras.items():
    cam.location=cpos
    cam.rotation_euler=(Vector((0.03,0.0,0.79))-cam.location).to_track_quat("-Z","Y").to_euler()
    bpy.context.view_layer.update()
    camera_pose={"location":[float(v) for v in cam.location],
                 "rotation":[float(v) for v in cam.rotation_euler],
                 "projection":"ORTHO","ortho_scale":float(cam.data.ortho_scale)}
    shots={}
    for name,delta in [("reference",0.0),("baseline",0.6),("m060",-0.6),("zero",0.0),("p060",0.6)]:
      neck.rotation_euler.z=source_angle+delta
      bpy.context.view_layer.update()
      stem=f"{cname}_f{frame}_{name}"
      blend=out/(stem+".blend")
      bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
      image=out/(stem+".png")
      sc.render.filepath=str(image)
      bpy.ops.render.render(write_still=True)
      shots[name]={"blend_sha256":sha(blend),"image_sha256":sha(image),"blend":blend.name,"png":image.name}
      if image.stat().st_size<200 or blend.stat().st_size<512:raise RuntimeError("empty native artifact")
    for name,delta in [("m060",-0.6),("zero",0.0),("p060",0.6)]:
      manifest={
       "schema":"scp.render_masks.v1",
       "experiment_id":f"pony_fit_{cname}_f{frame}_{name}",
       "baseline_sha256":shots["baseline"]["blend_sha256"],
       "candidate_sha256":shots[name]["blend_sha256"],
       "subject_class":"public_original_synthetic_equine",
       "camera_id":cname,"frame_index":frame,
       "split":"heldout",
       "mask_channel":"alpha","threshold":128,
       "reference":{"path":shots["reference"]["png"],"sha256":shots["reference"]["image_sha256"]},
       "baseline_render":{"path":shots["baseline"]["png"],"sha256":shots["baseline"]["image_sha256"]},
       "candidate_render":{"path":shots[name]["png"],"sha256":shots[name]["image_sha256"]}
      }
      mp=out/(f"manifest_{cname}_f{frame}_{name}.json")
      mp.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n")
      rows.append({"camera":cname,"frame":frame,"candidate":name,"delta_z_radians":delta,
                   "manifest":mp.name,"reference_type":"SYNTHETIC_SELF_RENDER",
                   "camera_pose":camera_pose,"shots":shots})
    neck.rotation_euler.z=source_angle
    bpy.context.view_layer.update()
receipt={"schema":"scp.native_neckfit_source.v1",
         "source_blend_sha256":source_sha,
         "source_rig_bones":len(rig.data.bones),
         "source_reference":"SYNTHETIC_SELF_RENDER_NOT_REAL_PHOTO",
         "optimizer":"THREE_POINT_FIXED_SWEEP_NOT_LLM",
         "visual_acceptance":"UNKNOWN","anatomical_acceptance":"UNKNOWN",
         "frames":frames,"camera_count":len(cameras),"candidate_deltas_radians":angles,
         "manifests":rows,"blender_version":bpy.app.version_string}
(out/"source_receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
print("SOURCE_ORIGINAL_NATIVE_MULTI_CAMERA_FIT_CANDIDATES",json.dumps({"manifests":len(rows),"frames":frames,"cameras":list(cameras)}))
