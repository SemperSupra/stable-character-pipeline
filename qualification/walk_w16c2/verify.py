"""Independent receipt, binary hashes and actual H264 settings."""
import hashlib,json,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1])
n=json.loads((p/"native_dual_leg_receipt.json").read_text())
g=json.loads((p/"third_gltf_vertex_receipt.json").read_text())
t=json.loads((p/"native_source_vertex_truth.json").read_text())
assert n["status"]=="PASS_ORIGINAL_TWO_ACTORS_TWO_LEGS_EACH_NATIVE_SKIN"
assert (n["actors"],n["legs_per_actor"],n["bones_per_actor"],n["vertices_per_actor"])==(2,2,4,56)
assert n["indexed_vertex_observations"]==784
assert n["maximum_native_import_world_xyz_error"]<=5e-4
assert n["native_ik_fk_max"]<=1e-3 and n["minimum_real_deformation"]>=.02
assert n["foot_contact"]=="NOT_QUALIFIED_NO_HEEL_TOE_LANDMARKS"
assert g["status"]=="PASS_PURE_STDLIB_GLTF_LBS_ANIMATION_INDEXED"
assert g["indexed_vertex_observations"]==784 and g["maximum_world_position_error"]<=5e-4
assert t["frames"]==[0,12,24,36,48,60,71]
assert n["glb_sha256"]==g["glb_sha256"]==t["glb_sha256"]
for name,key in (("original_two_actors_dual_leg.blend","blend_sha256"),
 ("original_two_actors_dual_leg.glb","glb_sha256"),
 ("original_two_actors_dual_leg_preview.mp4","video_sha256")):
 data=(p/name).read_bytes()
 assert len(data)>1000 and hashlib.sha256(data).hexdigest()==n[key]
data=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
 "-show_entries","stream=codec_name,width,height,nb_frames,r_frame_rate","-of","json",
 str(p/"original_two_actors_dual_leg_preview.mp4")]))
assert len(data["streams"])==1
v=data["streams"][0]
assert v["codec_name"]=="h264" and v["width"]==320 and v["height"]==180
assert v["r_frame_rate"]=="12/1" and int(v["nb_frames"])==72
print("W16C2_NATIVE_TWO_LEG_FOUR_BONE_THIRD_GLTF_H264_PASS",n["profile"],n["maximum_native_import_world_xyz_error"],g["maximum_world_position_error"])
