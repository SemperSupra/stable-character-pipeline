"""C3 independent exact versioned Go B3 typed packet to native Blender receipt."""
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1])
source=(p/"motion.json").read_bytes()
typed=json.loads(source)
n=json.loads((p/"native_dual_leg_receipt.json").read_text())
r=json.loads((p/"source_receipt.json").read_text())
g=json.loads((p/"third_gltf_vertex_receipt.json").read_text())
assert typed["Schema"]=="scp.walk_dual_leg_motion.v3"
assert typed["Rights"]==n["source_rights"]=="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
assert typed["OriginSHA"]=="e0a42b8d5dfe23334486ff195ac90fe6b7d3a199"
assert typed["ClockOrigin"]=="SYNTHETIC_ZERO_NO_MEASURED_CLOCK"
assert typed["FPSNum"]==12 and typed["FPSDen"]==1
assert typed["Basis"]=="BLENDER_RH_Z_UP_SOURCE"
assert typed["QuatOrder"]=="GLTF_XYZW_COMPONENTS_Z_UP_FRAME"
assert n["source_packet_sha256"]==hashlib.sha256(source).hexdigest()
assert n["source_packet_schema"]==typed["Schema"]
assert n["source_motion"]=="EXACT_B3_TYPED_DUAL_LEG_STREAM_TO_NATIVE_BLENDER"
assert n["indexed_vertex_observations"]==g["indexed_vertex_observations"]==784
assert n["native_ik_fk_max"]<=1e-3
assert n["maximum_native_import_world_xyz_error"]<=5e-4
assert g["maximum_world_position_error"]<=5e-4
assert n["foot_contact"]=="NOT_QUALIFIED_NO_HEEL_TOE_LANDMARKS"
assert r["SourceOnly"] and r["Observations"]==28 and r["MaxIKError"]<=1e-8
for i,a in enumerate(typed["Actors"]):
 assert a["ID"]==("CobaltOriginal","MarigoldOriginal")[i]
 for frame in a["Frames"]:
  assert frame["TimeNum"]==frame["Frame"] and frame["TimeDen"]==12
  assert all(leg["Contact"]=="unknown" for leg in frame["Legs"])
print("W16C3_B3_TYPED_SOURCE_TO_NATIVE_4BONE_784_W15_H264_PASS",
 typed["Profile"],n["source_packet_sha256"],n["native_ik_fk_max"],
 n["maximum_native_import_world_xyz_error"],g["maximum_world_position_error"])
