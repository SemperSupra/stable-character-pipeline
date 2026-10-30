# ROMFMT A: glTF/GLB source annotation preservation

Authority: ROM metadata DLE #175, ROM #170, VisualQA #150. Original fictional fixtures only.

`scp.rom.joint_annotation.v1` is separately versioned source JSON. Its SHA256 is bound to the derived `nodes[].extras.scp_rom_v1` annotation on each uniquely mapped `skins[].joints` node. The custom field includes joint ID, source authority, DOF kind, local basis, normalized axis, angular/linear units and synthetic hard range. Actual GLB magic/chunk and JSON bytes are decoded back to verify semantic equality; model binary SHA belongs in an outside receipt (never in the binary itself).

**GLB extras are NOT universally executed by glTF engines.** A green annotation-preservation test is not a biological ROM, robotic safety, runtime enforcement, IK, visual or full rig acceptance. Third-party exporters may omit these fields entirely. Missing or modified joint metadata is a hard preservation failure and must not be interpreted as unlimited motion.

The source helper intentionally rejects human/animal norm values, unsupported Euler/JCS frames and complex multi-DOF couplers. Those require a separate source-approved schema and independent evidence. No merge/release/deploy/paid/private workcell, CPE promotion. Small source/test receipts in Git/DLE. Large models in owner-private Drive only after rights, source SHA and full-byte rehydration custody.