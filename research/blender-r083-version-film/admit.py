"""Blender 5.x R083 source-safe 144f/24fps film admission. Independent of render scripts."""
import hashlib,json,math,sys
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,name):
 if not ok:raise ValueError(name)
def admit(build,video,version):
 require(version in ("5.2.4","5.3.0"),"UNKNOWN_RUNTIME")
 a=json.loads(Path(build).read_text());b=json.loads(Path(video).read_text())
 require(b.get("schema")=="scp.r083.dressed-144f-h264.v1","VIDEO_SCHEMA")
 require(b.get("source_class")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0","NOT_SOURCE_SAFE")
 require(b.get("frames_decoded")==144 and b.get("fps")==24,"VIDEO_CLOCK")
 require(b.get("same_scene_dressed_motion") is True,"DIFFERENT_SCENE")
 require(b.get("biomechanics_accepted") is False and b.get("cloth_dynamics_accepted") is False and
         b.get("mvp_accepted") is False and b.get("release_authorized") is False,"ILLICIT_PROMOTION")
 require(isinstance(b.get("video_sha256"),str) and len(b["video_sha256"])==64,"MISSING_REAL_VIDEO_DIGEST")
 require(isinstance(b.get("ffmpeg_wheel_sha256"),str) and
         b["ffmpeg_wheel_sha256"]=="c7e46fcec401dd990405049d2e2f475e2b397779df2519b544b8aab515195282","FFMPEG_WHEEL_UNTRUSTED")
 require(isinstance(a,dict) and bool(a.get("schema")),"NATIVE_SCENE_RECEIPT_ABSENT")
 return {"schema":"scp.blender5x.r083-native-film-qualification.v1",
  "version":version,"status":"PASS_NARROW_NATIVE_ORIGINAL_FILM",
  "real_ffmpeg_decode_frames":144,"fps":24,"native_actors_expected":2,
  "build_json_sha256":sha(build),"video_json_sha256":sha(video),
  "video_sha256":b["video_sha256"],"extension_compatibility_accepted":True,
  "render_visual_fidelity_accepted":False,"cloth_physics_accepted":False,
  "contact_gait_accepted":False,"protected_real_person_source_accepted":False,
  "mvp_accepted":False,"release_authorized":False}
if __name__=="__main__":
 try:
  if len(sys.argv)!=4:raise ValueError("USAGE")
  print(json.dumps(admit(*sys.argv[1:]),sort_keys=True,allow_nan=False))
 except (ValueError,TypeError,OSError,KeyError,RuntimeError) as e:
  print("SCP_BLENDER_5X_R083_FILM_RED",repr(e),file=sys.stderr);sys.exit(12)
