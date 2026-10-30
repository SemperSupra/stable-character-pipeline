"""Original synthetic W14 weighted 3D Blender scene -> actual 72 camera frames and authored stereo Foley.
Requires W14-generated .blend. Does not detect physical foot contact or assert human gait.
"""
import argparse, array, hashlib, json, math, subprocess, wave
from pathlib import Path
import bpy
from mathutils import Vector

RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
FPS,FS,FRAMES=12,48000,72
CUES=[12000+24000*i for i in range(12)]
ACTORS=("CobaltOriginal","MarigoldOriginal")
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source-blend",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 frames=out/"frames";frames.mkdir(exist_ok=True)
 source=Path(a.source_blend).resolve()
 bpy.ops.wm.open_mainfile(filepath=str(source))
 scene=bpy.context.scene
 scene.render.engine="BLENDER_WORKBENCH"
 scene.render.resolution_x=160;scene.render.resolution_y=90
 scene.render.resolution_percentage=100
 scene.render.image_settings.file_format="PNG"
 scene.render.image_settings.color_mode="RGB"
 scene.render.film_transparent=False
 scene.frame_start=0;scene.frame_end=FRAMES-1;scene.render.fps=FPS
 camd=bpy.data.cameras.new("OriginalPublicCamera")
 cam=bpy.data.objects.new("OriginalPublicCamera",camd)
 scene.collection.objects.link(cam);scene.camera=cam
 cam.location=(0,-7,2.25)
 cam.rotation_euler=(Vector((0,0,.75))-cam.location).to_track_quat("-Z","Y").to_euler()
 camd.type="ORTHO";camd.ortho_scale=5.2
 for name,color in zip(ACTORS,((.8,.35,.18,1),(.23,.56,.88,1))):
  arm=bpy.data.objects.get(name+"_Skeleton")
  mesh=bpy.data.objects.get(name+"_SkinnedMesh")
  if arm is None or mesh is None or arm.type!="ARMATURE" or mesh.type!="MESH":
   raise ValueError("W14_ORIGINAL_WEIGHTED_SOURCE_NOT_FOUND")
  if arm.get("source_rights")!=RIGHTS or mesh.get("source_rights")!=RIGHTS:
   raise ValueError("SOURCE_RIGHTS_NOT_ADMITTED")
  if not any(m.type=="ARMATURE" for m in mesh.modifiers):
   raise ValueError("WEIGHTED_SKIN_MISSING")
  mesh.color=color
 root=[]
 for i in range(FRAMES):
  scene.frame_set(i)
  move=.70*(i/(FRAMES-1))
  for k,name in enumerate(ACTORS):
   arm=bpy.data.objects[name+"_Skeleton"]
   arm.location.x= (-1.65+move) if k==0 else (1.65-move)
  bpy.context.view_layer.update()
  source_roots=[float(bpy.data.objects[name+"_Skeleton"].matrix_world.translation.x) for name in ACTORS]
  if source_roots[0]>=source_roots[1]:
   raise ValueError("ACTOR_WORLD_ROOT_ORDER_CHANGED")
  root.append(source_roots)
  scene.render.filepath=str(frames/f"{i:04d}.png")
  bpy.ops.render.render(write_still=True)
  if (frames/f"{i:04d}.png").stat().st_size<100:
   raise ValueError("MISSING_NATIVE_BLENDER_FRAME")
 pcm=array.array("h",[0])*(FS*6*2)
 for i,start in enumerate(CUES):
  channel=i%2
  for j in range(32):pcm[2*(start+j)+channel]=int(12000/(j+1))
 audio=out/"original_stereo_foley.wav"
 with wave.open(str(audio),"wb") as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(FS);w.writeframes(pcm.tobytes())
 media=out/"original_3d_camera_foley_master.mkv"
 subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(FPS),
 "-i",str(frames/"%04d.png"),"-i",str(audio),"-c:v","ffv1",
 "-c:a","pcm_s16le","-fps_mode","passthrough","-shortest",str(media)],
 check=True,timeout=120)
 if media.stat().st_size<1000:raise ValueError("NATIVE_MUX_EMPTY")
 receipt=dict(schema="scp.spatial_w4h_original_3d_av.v1",
   status="NATIVE_BLENDER_WEIGHTED_ACTOR_ANNOTATED_AV_PRODUCED",
   source_rights=RIGHTS,source_blend_sha256=digest(source),
   video_frame_rate=[FPS,1],video_frames=FRAMES,audio_hz=FS,
   audio_samples=FS*6,contact_authority="SELF_AUTHORED_ANNOTATION_NOT_GEOMETRY_DETECTED",
   stereo_foley_source_samples=CUES,actor_root_x=root,
   source_audio_sha256=digest(audio),actual_media_sha256=digest(media),
   first_frame_sha256=digest(frames/"0000.png"),
   last_frame_sha256=digest(frames/"0071.png"),
   scope="SOURCE_ANIMATED_3D_SKIN_CAMERA_NOT_3D_HEEL_CONTACT_OR_SOLVER_EQUIVALENCE")
 (out/"w4h_3d_source_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
 print("W4H_NATIVE_BLENDER_WEIGHTED_3D_AV_OUTPUT_READY frames=72 contacts=12")
if __name__=="__main__":main()
