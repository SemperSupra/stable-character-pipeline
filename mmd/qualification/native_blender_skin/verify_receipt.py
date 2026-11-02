#!/usr/bin/env python3
"""Independent typed actual bpy review, never conflate synthetic with real acceptance."""
import json,math,pathlib,sys
p=pathlib.Path(sys.argv[1]);r=json.loads(p.read_text())
assert r["schema"]=="scp.mmd.native_bpy_original_skin.v1"
assert r["status"]=="PASS_ACTUAL_BLENDER45_MMD_TOOLS_VMD_IMPORT_AND_SYNTHETIC_SKIN_ONLY"
assert r["original_vmd_sha256"]=="3b20c6822337dab0078d32a2d65f7ead2d11716db5e5500b619d3218b4439b94"
assert r["blender_version"].startswith("4.5.")
assert r["mmd_tools_commit"]=="f1d8a98db5e185cfa73c9b8a8a67fa42d9eb4b14"
assert r["actual_bpy_pose_track_count"]==3
assert r["actual_skinned_meshes"]==2
assert len(r["frame_0_to_30_joint_displacement"])==3
assert len(r["frame_0_to_30_skinned_mesh_displacement"])==2
for values in ("frame_0_to_30_joint_displacement","frame_0_to_30_skinned_mesh_displacement"):
 for d in r[values].values():assert math.isfinite(d) and .9<=d<=1.1
assert r["frame0_rewind"]=="PASS_NUMERIC_TOLERANCE_1E_MINUS_7"
assert r["human_mocap"]=="NOT_ADMITTED" and r["native_standalone_MMD"]=="NOT_RUN"
assert r["PMX_specific_rig"]=="NOT_RUN" and r["genuine_human_skin"]=="NOT_RUN"
assert r["visual_gait"]=="UNKNOWN" and r["anatomy_rom_jcs"]=="UNKNOWN"
assert r["protected_R009"]=="HELD_NOT_ACCEPTED"
print("PASS_INDEPENDENT_NATIVE_BPY_EVIDENCE_NONPROMOTING")
