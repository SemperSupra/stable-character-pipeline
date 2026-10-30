"""Independent numeric receipt/codec/count guard. No Blender or video decoder requalification."""
import hashlib,json,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1])
n=json.loads((p/"native_3d_skin_receipt.json").read_text())
r=json.loads((p/"pure_gltf_vertex_receipt.json").read_text())
truth=json.loads((p/"native_source_vertex_truth.json").read_text())
video=p/"original_integrated_3d_ik_preview.mp4"
glb=p/"original_two_weighted_3d_characters.glb"
blend=p/"original_two_weighted_3d_characters.blend"
assert n["status"]=="PASS_BLENDER_NATIVE_TWO_WEIGHTED_3D_AND_GLB_REIMPORT"
assert n["source_motion"]=="ORIGINAL_EXPLICIT_ANALYTIC_3D_IK_ROOT_WALK_NOT_MEASURED_GAIT"
assert n["imported_evaluated_vertex_observations"]==392
assert n["maximum_world_vertex_error"]<=.0005
assert n["minimum_actor_deformation"]>=.02
assert r["status"]=="PASS_PURE_STDLIB_GLTF_LBS_ANIMATION_INDEXED"
assert r["indexed_vertex_observations"]==392
assert r["maximum_world_position_error"]<=.0005
assert truth["glb_sha256"]==r["glb_sha256"]==hashlib.sha256(glb.read_bytes()).hexdigest()
for path,field in [(glb,"glb_sha256"),(blend,"blend_sha256"),(video,"video_sha256")]:
    assert path.exists() and path.stat().st_size>1000
    assert n[field]==hashlib.sha256(path.read_bytes()).hexdigest()
media=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
 "-show_entries","stream=codec_name,width,height,nb_frames,r_frame_rate","-of","json",str(video)]))
streams=media["streams"];assert len(streams)==1
s=streams[0]
assert s["codec_name"]=="h264" and s["width"]==320 and s["height"]==180
assert s["r_frame_rate"]=="12/1" and int(s["nb_frames"])==72
print("W16C_NATIVE_IK_NATIVE_SKIN_THIRD_GLTF_H264_PASS",
      "native_xyz",n["maximum_world_vertex_error"],
      "independent_xyz",r["maximum_world_position_error"],"video_sha256",n["video_sha256"])
