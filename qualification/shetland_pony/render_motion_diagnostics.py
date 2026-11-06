#!/usr/bin/env python3
"""Read-only, deterministic multiview 48-frame diagnostic render.

Runs on the native integrated .blend. Renders actual evaluated geometry at
each frame; frame artifacts are ephemeral and encoded by ffmpeg in the CI job.
No simulation inference, export certification, protected media or acceptance.
"""
import bpy
import hashlib
import json
import sys
from pathlib import Path

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:]) != 2:
    raise SystemExit("usage: blender -b --python render_motion_diagnostics.py -- <joined.blend> <outdir>")
scene_file, output = map(Path, sys.argv[sys.argv.index("--")+1:])
if not scene_file.is_file():
    raise FileNotFoundError(scene_file)
output.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(scene_file.resolve()))
scene=bpy.context.scene
rig=bpy.data.objects.get("PonyRig30")
if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=30:
    raise ValueError("source armature and original 30-joint topology missing")
if scene.frame_start>1 or scene.frame_end<48:
    raise ValueError("48 frame source sequence unavailable")
views=[
    ("side",scene.camera),
    ("face",bpy.data.objects.get("FacialCloseupQA")),
    ("tail",bpy.data.objects.get("TailRearQA")),
    ("mane",bpy.data.objects.get("HairDetailQA_mane")),
]
if any(camera is None or camera.type!="CAMERA" for _,camera in views):
    raise ValueError("missing one or more native evidence cameras")
if len(set(camera.name for _,camera in views))!=len(views):
    raise ValueError("duplicated camera viewpoint")
original_camera=scene.camera
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
scene.render.resolution_x=640
scene.render.resolution_y=420
scene.render.resolution_percentage=100
scene.render.film_transparent=False
scene.render.use_file_extension=True
# Explicitly restrict the disposable four-view diagnostic to 2 CPU Cycles
# samples. High-quality native stills remain a separate appearance evidence
# lane; 192×16-sample renders waste $0 runner resources for motion inspection.
if scene.render.engine=="CYCLES":
    scene.cycles.samples=2
receipt={"schema":"equine.motion.fourviews.v1",
         "source_sha256":hashlib.sha256(scene_file.read_bytes()).hexdigest(),
         "fps":24,"frames_per_camera":48,"views":{},"quality":"diagnostic, not visual or biomechanics acceptance"}
for name,camera in views:
    scene.camera=camera
    folder=output/"frames"/name
    folder.mkdir(parents=True,exist_ok=True)
    hashes=[]
    sizes=[]
    for frame in range(1,49):
        scene.frame_set(frame)
        target=folder/("frame_%03d.png"%frame)
        scene.render.filepath=str(target)
        bpy.ops.render.render(write_still=True)
        if not target.exists() or target.stat().st_size < 2000:
            raise ValueError("empty diagnostic frame "+name+":"+str(frame))
        data=target.read_bytes()
        hashes.append(hashlib.sha256(data).hexdigest())
        sizes.append(len(data))
    if len(set(hashes))<5:
        raise ValueError("view contains too few visually distinct frames: "+name)
    receipt["views"][name]={"camera":camera.name,"unique_png_sha256":len(set(hashes)),
                              "frames":len(hashes),"total_png_bytes":sum(sizes),
                              "first_frame_sha256":hashes[0],"last_frame_sha256":hashes[-1]}
    print("NATIVE_ACTUAL_FRAME_MOTION",name,len(set(hashes)),sum(sizes))
scene.camera=original_camera
(output/"diagnostic_frames_receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
print("MOTION_DIAGNOSTIC_RENDERED_4VIEWS_48F",str(output))
