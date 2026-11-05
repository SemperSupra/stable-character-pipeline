# Agent-plan-bound native reconstruction experiment (candidate-only)

This is a **child** of [draft native multiview #309](https://github.com/SemperSupra/stable-character-pipeline/pull/309), with the Go bounded actor policy source frozen at [draft #306](https://github.com/SemperSupra/stable-character-pipeline/pull/306), exact commit `57d1d5792ffaaf033f4035b859b0bca2dc088c3d`. Its source-original 26-bone pony model and the independent Go decoded-PNG pixel comparator are unchanged. Both belong to public original synthetic workcells.

## Actually executed control flow

1. Public GHCR Blender 4.5.15 rebuilds the 26-bone synthetic pony at immutable producer commit `1f2febbd28d508d1c3d9f2a644f861d634f65a9d`.
2. SHA256-check the generated model `.blend` and its synthetic source `.glb`; `plan_bridge.py make` emits the exact source-bound `scp.actor_parameter_plan.v1` proposal.
3. Run the independently frozen Go policy from #306 (not an LLM). It validates typed joint `neck`, local axis `Z`, public-original synthetic evidence class, bounded angles [-0.6,0.6], exactly three candidate IDs, and candidate-only intent.
4. `plan_bridge.py check` independently recomputes Go candidate IDs, rejects stale model and evidence bytes, unknown fields, duplicates, angle expansion and promotion. A bound JSON gate is emitted.
5. **The native Blender candidate producer now requires this gate** and rechecks source/evidence bytes before changing the 26-bone armature or creating 2 cameras × 2 frames × 3 candidate images.
6. A separate standard Ubuntu job independently reads and rechecks the bound plan, Blender source states, SHA256 of scene and PNG bytes, and computes real decoded-pixel IoU. Fail/unknown science is preserved.

No LLM/VLM inference is claimed in this workcell; a future reasoning actor can propose the same approved schema through an authenticated admission path. No external photograph, no equine anatomical prior, no actual shape optimization, no body sculpting or photogrammetric camera calibration. The GLB is source-generated synthetic evidence, **not a photograph or external holdout**. The resulting exact-source experiment only proves that a typed actor proposal actually controls the native candidate parameters; it does not prove identity, geometry quality, biological joint correctness, or gait.

## Three audiences and housekeeping

Human review: inspect the native contact sheet, actual source/view/receipt hashes, numeric scores and physical/anatomical UNKNOWNs. Automation: JSON proposal → Go plan → Python bound gate → Blender scene → independent PNG/image and source receipts. Agents: typed candidate-only proposal; no direct arbitrary `bpy` or shell execution exposed.

This child modifies inherited `qualification/agent_native_neckfit/pony_fit_blender.py` and `.github/workflows/scp-native-neckfit.yml` **within stacked ancestry**, not independent sibling source ownership. Novel additions are `plan_bridge.py`, its hostile unit tests and this document. Parent #309 remains unchanged at `f1e972ebfe8d00313cc238a6417d4cfc24aaef42`; reviewer must check exact branch/CI before adoption. Records and code belong in Git/DLE; large original public synthetic render and model binaries in owner-private Drive with whole-byte SHA readback. A successful workflow is engineering-only, **not** a release, source merge, deployment or CPE acceptance.

Per-batch DOPAV closeout: observe exact head and source rights; inspect first failure including logs; verify independent job and artifact hash; reconcile active child-parent and separate owner branches; record disposition (retain, resolve, merge only when authorized, or close truly terminal duplicate) and next baton. Never delete first failures. Existing private R009 #23 / G5/G9 #103 and photo/media holds remain.
