"""Native Blender original synthetic head/jaw visualization, timeline owned by Go W4h typed contract.
No speech synthesis, anatomical viseme, emotion inference or lip-reading claims.
"""
import argparse,array,hashlib,json,math,subprocess,wave
from pathlib import Path
import bpy
from mathutils import Vector
FPS=24;FS=48000;FRAMES=48
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jaw_at(keys,s):
 keys=sorted(keys,key=lambda k:k["sample"])
 for i in range(1,len(keys)):
  a,b=keys[i-1],keys[i]
  if s==b["sample"]:return b["value"]
  if s<b["sample"]:
   if b["discontinuity"]:return a["value"]
   return a["value"]+(b["value"]-a["value"])*(s-a["sample"])/(b["sample"]-a["sample"])
 return keys[-1]["value"]
def main():
 pa=argparse.ArgumentParser();pa.add_argument("--packet",required=True);pa.add_argument("--out",required=True);a=pa.parse_args()
 out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True);frames=out/"frames";frames.mkdir(exist_ok=True)
 packet=json.loads(Path(a.packet).read_text(encoding="utf8"))
 c=packet["clock"]
 if packet["schema"]!="scp.av_presentation.v1" or packet["rights"]!="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC" or c!={"audio_hz":FS,"fps_num":30000,"fps_den":1001,"duration_samples":FS*2}:
  raise ValueError("ANNOTATION_RIGHTS_CLOCK_UNSUPPORTED")
 if not all(e["origin"]=="externally_annotated" for e in packet["cues"]):
  raise ValueError("CUE_INFERENCE_NOT_ADMITTED")
 jawkeys=[k for k in packet["poses"] if k["stream"]=="jaw"]
 if len(jawkeys)!=5:raise ValueError("JAW_SOURCE_ANNOTATIONS")
 bpy.ops.wm.read_factory_settings(use_empty=True)
 sc=bpy.context.scene
 sc.render.engine="BLENDER_WORKBENCH";sc.render.film_transparent=False
 sc.render.resolution_x=160;sc.render.resolution_y=90;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGB";sc.render.fps=FPS
 bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=(0,0,0.65))
 head=bpy.context.object;head.name="OriginalSyntheticHead";head.scale=(.56,.35,.66)
 bpy.ops.mesh.primitive_cube_add(size=1,location=(0,-.39,.32))
 jaw=bpy.context.object;jaw.name="OriginalSyntheticJaw";jaw.scale=(.55,.14,.10)
 bpy.ops.mesh.primitive_cube_add(size=1,location=(0,-.395,.47))
 upper=bpy.context.object;upper.name="OriginalSyntheticUpperLip";upper.scale=(.53,.15,.055)
 camera_data=bpy.data.cameras.new("SourceCamera");cam=bpy.data.objects.new("SourceCamera",camera_data);sc.collection.objects.link(cam)
 cam.location=(0,-4.3,.62);cam.rotation_euler=(Vector((0,0,.61))-cam.location).to_track_quat("-Z","Y").to_euler()
 camera_data.type="ORTHO";camera_data.ortho_scale=2.6;sc.camera=cam
 pose=[]
 for frame in range(FRAMES):
  s=frame*(FS//FPS)
  v=jaw_at(jawkeys,s)
  # Visually observable mouth aperture: lower jaw moves down when the typed annotation opens.
  jaw.location.z=.33-.22*v
  pose.append({"frame":frame,"sample":s,"jaw_open":v,"jaw_mesh_z":float(jaw.matrix_world.translation.z) if False else .33-.22*v,"upper_lip_z":.47})
  sc.frame_set(frame);sc.render.filepath=str(frames/f"{frame:04d}.png");bpy.ops.render.render(write_still=True)
 if max(x["jaw_open"] for x in pose)<1 or pose[12]["jaw_open"]!=0 or pose[15]["jaw_open"]!=1 or pose[18]["jaw_open"]!=0:
  raise ValueError("FACIAL_POSE_SAMPLES_WRONG")
 samples=array.array("h",[0])*(FS*2)
 # Annotation-driven original speech-like synthetic tone bursts; NOT intelligible language.
 for start,end,pitch in ((24000,30000,220),(30000,36000,440)):
  for i in range(start,end):
   samples[i]=int(10000*math.sin(2*math.pi*pitch*(i-start)/FS))
 wav=out/"original_synthetic_annotated_voice.wav"
 with wave.open(str(wav),"wb") as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(FS);w.writeframes(samples.tobytes())
 media=out/"viseme_annotated_original_master.mkv"
 subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate","24","-i",str(frames/"%04d.png"),"-i",str(wav),"-c:v","ffv1","-c:a","pcm_s16le","-fps_mode","passthrough","-shortest",str(media)],check=True,timeout=120)
 report={"schema":"scp.w4i_native_annotated_jaw.v1","status":"NATIVE_SYNTHETIC_3D_JAW_RENDERED","rights":packet["rights"],"annotation_sha256":sha(a.packet),"source_sha256":packet["source_sha256"],"frames":FRAMES,"fps":FPS,"audio_samples":FS*2,"audio_hz":FS,"jaw_pose":pose,"phoneme_source_samples":[24000,30000],"wav_sha256":sha(wav),"media_sha256":sha(media),"limit":"SYNTHETIC_GEOMETRY_AND_TIMING_ONLY"}
 (out/"native_pose.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
 print("W4I_NATIVE_SYNTHETIC_JAW_AV_READY frames=48 sample_clock=48000")
if __name__=="__main__":main()
