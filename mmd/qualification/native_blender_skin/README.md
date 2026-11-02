# Actual Blender 4.5.15 + pinned MMD Tools v4.5.14 native skinning qualification

Independent workcell stacked on source-safe upstream reader #251 and VMD source-fix #250. Uses official Blender Foundation 4.5.15 binary downloaded on public Actions, verified by Blender's own published SHA256; upstream GPL-3.0+ MMD Tools v4.5.14 checked-out commit `f1d8a98db5e185cfa73c9b8a8a67fa42d9eb4b14` is transient, not vendored. No sensitive files or paid/private minutes.

Runs the actual `mmd_tools.core.vmd.importer.VMDImporter.assign()` with a 93-keyframe original authored VMD from the corrected Go source, a real native `bpy` armature of three authored bones, two 4-vertex one-bone-weight synthetic quads, and real `ARMATURE` modifiers. Checks pose and evaluated skinned geometry at frames 0/30 and rewind; independent Python verifies actual numeric evidence. This is **engineering/format proof**, not independent original mocap, human anatomy, physical contact, PMX-specific semantics, MMD app playback, skinning of actual Naomi/Alison, historical choreography or R009 acceptance.

Human README, automation JSON receipt, agent can inspect published contract/replay command; no live agent write hooks. Native test must pass exact public CI before claiming any actual bpy acceptance. First native failure is retained; no automatic merge, release, deployment, CPE or authentic-source promotion.
