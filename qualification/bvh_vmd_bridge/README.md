# R009 public-original synthetic BVH → VMD → Blender bridge

This is a source-safe engineering-only workcell, **not** human skeletal retargeting, biological ROM qualification, measured mocap, a protected-character render, or an approved release.

## Frozen donor contracts
- Public original-author BVH #249: exact source fixture SHA-256 `ab3a0d712c9c4f21fba0cf0698568dd5f88f1b959cf8aae28173c6435153d760`. Three synthetic joints, three ticks at an exact rational approximation to 60 Hz; a source-meters-per-unit value must be explicitly supplied.
- Public corrected VMD #250 supplies the actual tested v2 writer and byte reader. This branch copies its **unchanged** version from the verified upstream #252 ancestry for one native workflow and renames only the CLI main entry point in a temporary runner directory.
- Native importer: official, SHA-verified Blender 4.5.15 LTS and unmodified maintained MMD Tools 4.5.14 checkout commit `f1d8a98db5e185cfa73c9b8a8a67fa42d9eb4b14`.

## Explicit loss / mapping contract
The three original joint world-position translations are tested against an unparented synthetic target rig. **Preserve the source names exactly:** `Hips→Hips`, `Knee→Knee`, `Foot→Foot`. No arbitrary knee-to-ankle aliases. This is a **world-translation-only bridge**, not a hierarchical skeleton retargeter: source local rotations, segment hierarchy, mass/contact and human/animal ROM are not preserved. Source frames 0 and 2 at 60 Hz map to VMD frames 0 and 1 at 30 Hz; source frame 1 is explicitly dropped. Retain the lost-tick/axis/units/rights statements in typed JSON evidence.

**First native zero-motion root cause established from pinned upstream source:** `mmd_tools/core/vmd/importer.py` commit `f1d8a98d` captures `bpy.context.scene.frame_current` during `VMDImporter.__init__` (upstream line 276) and adds it to each VMD keyframe (upstream line 501). Fresh Blender defaults to **frame 1**. Earlier tests sampled Blender frames 0 and 1 after importing source VMD frames 0 and 1 at **Blender 1 and 2**, so all three bones and skins looked frozen despite a valid 6-key binary. This is a **time-origin mismatch**, not evidence for nonworking bone names. Force and verify scene frame 0 before constructing the original upstream importer; do not weaken the real movement guard. Preserve first native failure runs `41561099277`, `41561667476` and alias-only `41562234366` as distinct REDs pending exact-head rerun.

## Execute, observe, verify
Public PR workflow `.github/workflows/r009-bvh-vmd-bpy.yml` uses **standard $0 public Actions**, no secrets or protected originals. It runs preflight Go FK against immutable #249; five source/clock/issuer/joint-tamper negatives; corrected VMD serialization/byte verification; and real Blender `VMDImporter.assign` plus native skinned mesh displacement and frame rewind, with explicit scientific UNKNOWN / protected HELD statuses. Read actual run ID and exact commit head before claiming PASS.

Original first RED `41547845730` was malformed Go newline syntax (fixed without changing semantics). Follow-up native RED `41561099277` and diagnostic RED `41561667476` showed all three generic named bones stationary in native Blender despite successful VMD byte checks. Rather than decrease motion thresholds, the current candidate introduces an **explicit lossy adapter alias** to the names already independently qualified by native #252. Current candidate must be verified on its own head; until then the native result remains UNKNOWN/RED.

## Admission / audiences
Human: this scope, fault and loss map, test links and receipts. Automation: JSON manifests and strict nonoverwriting CLI/workflow evidence. Agent: observe/capability exploration of source-safe receipts only; no protected apply or private promotion. All first failures retained. Source/rights/custody/performer, protected runner, authentic R009 original bodies, JCS/ROM/contact/visual quality, CPE blind, merge, release, deployment **HELD**.
