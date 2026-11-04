# R009 — explicit-target humanoid IK and stance controller (source-only candidate)

**State:** independently executable pure-Python source-only research. **NOT** adapted to, installed on, or verified against any native Blender armature. NOT an accepted gait, biomechanical solver, or real-person animation. No raw assets, private runner, protected human/vendor material, or CPE admission. Owning public DLE: [#272](https://github.com/SemperSupra/stable-character-pipeline/issues/272); private original/product holds: private DLE #23.

## Why the current rig is insufficient

The source-authorized Microsoft Rocketbox MIT original two-character rig has 80 bones and true skin deformation, but authored local-Z 72f gait showed 51 near-ground candidate sliding intervals above 8 cm/frame across L/R feet of two actors in independent V3 native Blender observation. V4 root-only timing changed on actual original native render, but moving a root cannot guarantee any foot stays planted in world coordinates. Original private Naomi 15-bone skin and Alison 80-bone sourced FBX have separate private visual/skin/contact failures. Do not assume a bone count alone proves locomotion or any other action.

## Implemented and runnable here

- `rig_control.py`: deterministic source-only 3D analytic two-segment IK for **either arm or leg**, explicit world-space bend-pole, rejected unreachable targets and degenerate pole/lengths. No arbitrary Euler-axis dependence. It returns joint world points, *not* Blender pose bone rotations.
- Explicit `Stance(start,end,world_foot_anchor)` intervals, invariant stance targets, timed smooth swing with vertical clearance and no false contact claim. No near-ground screen color/weighted centroid used as a force/contact oracle.
- Two-side/fixed-clock IK contract that fails on misaligned frames and retains `native_80_bone_skin_verification: NOT_RUN` and `mvp_accepted:false` regardless of source-only results.
- `test_rig_control.py`: 11 independent tests including 72-frame two-foot geometry, mirror bends, pole-axis degeneracy, unattainable targets, NaN and booleans, contact discontinuities and explicit stance locks.
- Reproduce at $0 with `python3 -m unittest -v test_rig_control.py` from this folder; no packages or network necessary.

## Native engineering ladder (not yet implemented)

1. **REST/ROLE DISCOVER**: On frozen source Blender rig, obtain bone heads/tails, rest matrices, side/axis/parent hierarchy, original weight maps, joint limits, hip/ankle/toe/heel source landmark confidence and a right/left/top/bottom rig visualization. Reject ambiguous or contradictory bone axes and source/rights mismatch; do not change donor rig in-place.
2. **NONDESTRUCTIVE CONTROL RIG**: Add a separately named root/pelvis control, explicit heel/toe/ball pivot, world-space planted foot target and knee pole, foot-roll/ankle articulation and IK/FK switching; arm reach/elbow pole and retarget semantics are independent. Transfer output to source bones *in their measured rest frames*. No guessed Euler signs.
3. **SOURCE-SKIN OBSERVE**: Evaluate *the actual weighted foot/Toe0 original mesh in native Blender* over full 72×2×2 frames, both front/oblique cameras, preserving unchanged six official MIT textures. Independently assert foot travel while **declared support** is active, penetration/hover against actual walkway, swing clearance, 3D knee/hip ROM constraints and mesh strain; include first-failure evidence. A planted target alone never qualifies weighted sole material.
4. **PROGRESSIVE ACTIONS**: walk → idle/start/stop/turn → faster walk/run → sit/stand → stairs → reaching/carrying. Each receives its own discrete contact/pose/state clock, native pose sweep, deformation falsifiers and independent human review before adoption. Do not conflate technical render PASS, controller math PASS and anatomical/identity/behavior PASS.
5. **THREE AUDIENCES**: Human timeline/pose-controls and side-by-side visual QA; automation JSON schema and exact SHA receipts; agent read-only capabilities and explicit typed workflow states. Highest quality state is `HUMAN_APPROVED`, never self-awarded by tool output.

## Original failure retained

R009 original V3 independent real weighted-sole native 51 candidate sliding intervals, max 0.179488 m/frame; V4 has no independent native foot measurement. Conditional root-step triangle bound on recorded original V3 measured intervals and V4 source-native root path leaves at least 43 intervals above 0.08 m/frame **if local poses and skin remain unchanged**. This is a read-only geometric bound; no physical ground-contact certification or new Blender V4 source run is implied. A separate V4 source-native reviewer write was previously explicitly blocked; **do not recreate or route around that reviewer**. This independent control study is not such a reviewer and does not modify its source.

## Lifecycle

One independent source writer, frozen base, source/test/doc/workflow paths confined to this workcell; source-only CI must be green before future native integration. Independent native observer and visual human reviewer must qualify actual model motion before release. No protected original assets in public workflows. Product identity, rights and CPE/merge/release/deploy holds remain intact; retire or merge only with explicit owner gate and evidence.
