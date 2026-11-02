#!/usr/bin/env python3
"""Independent native engine result receipt/custody claims; fail closed on scientific promotion."""
import json,math,pathlib,sys
r=json.loads(pathlib.Path(sys.argv[1]).read_text())
assert r["schema"]=="scp.mmd.actual_blender_mmd_tools_original_vmd.v1"
assert r["status"]=="PASS_AUTHORED_SYNTHETIC_BLENDER45_MMD_TOOLS_IMPORT_AND_ACTUAL_SKIN_DEFORM_ONLY"
assert r["plugin_source_ref"]=="fc6411d0fb0dd690cae8cf8eb1fae14311e756cc"
assert r["blender_version"].startswith("4.5.")
assert r["upstream_imported_tracks"]==3 and r["upstream_imported_keyframes_per_track"]==31
for d in r["bone_frame_0_to_30_displacements"].values(): assert math.isfinite(d) and .99<=d<=1.01
assert len(r["bone_frame_0_to_30_displacements"])==3
assert len(r["skinned_mesh_frame_0_to_30_displacements"])==2
for d in r["skinned_mesh_frame_0_to_30_displacements"].values(): assert math.isfinite(d) and .99<=d<=1.01
assert r["frame0_after_rewind"]=="BYTE_EQUIVALENT_NUMERIC_WITH_TOLERANCE"
assert r["measured_human_mocap"]=="NOT_ADMITTED" and r["private_R009"]=="HELD_NOT_RUN_NOT_ADMITTED"
assert r["genuine_PMX_MMD_target"]=="NOT_RUN" and r["standalone_MMD_runtime"]=="NOT_RUN"
assert r["physical_contact"]=="UNKNOWN" and r["anatomy_JCS_ROM"]=="UNKNOWN"
print("PASS_INDEPENDENT_NATIVE_BOUND_RECEIPT_HOLDS")
