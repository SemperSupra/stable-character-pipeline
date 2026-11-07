# R009 MakeHuman35 — skirt yoke and 73-pose contact research (2026-11-07)

**Status: retained as a reversible, original-only RESEARCH candidate. Not a realistic human, cloth solver, visually approved outfit, native Blender fit, or release candidate.**

## Source and ownership

Reuse the existing R009 DLE #272 and stacked draft PR #336. The admitted parent is **source-original fictional Aster/Juniper plus pinned MakeHuman CC0 body only**. Exact source GLB SHA256 `ae2b809ffa5cf5dfee0adf2f6b88b0a864e3588b95638de4c8b86e83a6e524af` (prior successful Juniper-only armhole relative trial). The *actual resulting trial* GLB SHA256 `b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748`. No protected Naomi/Alison inputs or vendor artifacts were used. Retarget source, Aster, rig, animation and all wardrobe library meshes remain unchanged.

## Root cause and independent batches

1. **Contact face atlas.** Full source-bound 9-pose VTK face-ID capture verifies repeated Juniper bodice intersections at face IDs **641 and 703 in all 9 sample states**, and localized skirt faces in the hip/thigh yoke (roughly local y=0.69–0.81 m, lateral negative X during frame 16). Aster bodice also intersects on those 2 faces plus additional shoulder faces. This is a *contact localization* witness, not proof of an anatomically valid fix. A separate source-free positive/negative VTK control prevents empty-contact false passes.
2. **Skirt weights.** Independent glTF inspection found **320/320 source skirt vertices per actor weighted 100% to spine**. New `skirt_yoke_weight_trial_v1.py` keeps the exact 320 vertices / 512 triangles, but adds bounded per-ring pelvis and left/right hip influences, smoothly tapering to the rigid spine waist. New JOINTS_0/WEIGHTS_0 accessors and a new mesh are appended; original source buffer prefix is identical. The only active node changed is `JuniperOriginal_Wardrobe_costume_bottom`. No vertex deletion or artifice to hide contact triangles.
3. **Falsification and parameter screen.** Initial profile strength=0.35, hip_share=0.30 reduced Juniper triangle pairs 1317→999 but **eight individual frames worsened**; rejected. Another profile 0.30/0.70 reduced 1317→741 but **three frames worsened**; rejected. The recorded screening sweeps include both failed and successful parameters, not just the winning sample.
4. **73-pose paired contact audit, 72-frame skin strain.** Bounded profile strength=0.35, hip_share=0.80, source-hash-bound and independently second-built byte-identical: Juniper skirt **1317→526 triangle crossing pairs across rest+72**, **51 improved states / zero worsened**. Signed negative >5mm vertex mean **0.00569349→0.00085616**, maximum **0.01875→0.00625**, **30 improved states / zero worsened**. All other garment slots and Aster unchanged: 81 total contact improvements, zero contact regressions. The standalone baseline rigid skirt has p99 edge ratio ≈1.000001; weighted trial p99 ≤1.093258, max edge ratio ≤1.102691, minimum ratio ≥0.875487, minimum triangle area ratio ≥0.850306, and zero edges with >50% severe strain in each 72-frame sample.

## Validator red/blue assessment

A rigid skirt cannot deform naturally, so requiring exactly zero **additional** strain relative to a 100%-spine baseline would reject *every* useful skinned skirt. Rather than weakening the existing strict contact comparator, `skirt_bounded_research_gate_v1.py` composes two independently preserved witnesses:

- Non-negotiable **zero triangle-contact and signed-vertex regressions** across all 73 states, with strict actor/slot/source/hash/clock/false-approval gates.
- A separately labeled **research-only bounded deformation envelope** (p99 and max edge ratio ≤1.15; minimum edge ratio ≥0.80; minimum area ratio ≥0.80; zero severe >50% strain). These are **engineering research thresholds, not physical clothing acceptance criteria**, and must be revised by actual reference-body data and image inspection rather than silently changed.

Any source drift, skipped frame, forged success flag, changes outside Juniper skirt, contact worsening, non-finite value or envelope violation rejects the candidate. The gate returns **PASS_BOUNDED_RELATIVE_RESEARCH_ONLY** but all physics, release, human realism, natural gait and native Blender approval flags remain FALSE.

## Visual QA and remaining RED

The actual front camera at animation frames 16 and 71 exposes a stiff, oversimplified flared skirt and thigh/hip contact that remains visually poor. The new weights improve the measured fit, but **526 triangle crossings still occur** over the sequence and the upstream source body retains mannequin-like anatomy and stylized hands. No real cloth simulation, drape, UV/pattern design, friction, floor response or full Blender evaluated triangle BVH has been accepted.

Next producer priority: reauthor a real skirt yoke, thigh/hem seam panels and character-specific patterns; pair with native Blender 72-frame BVH and multi-camera diagnostic renders, plus human acceptance. Correct Juniper bodice shoulder strips (repeated face IDs 641/703); don't delete faces simply to game collision counts. Retain all original source assets and parent #308/#336 stacked-base drift hold. Never merge, release, CPE, close or delete the owner branches from a relative research pass.

## Reproduction and custody

From `qualification/parametric_humans` with exact admitted GLB and NumPy/SciPy/VTK available:

```sh
python3 -m unittest -v test_contact_hotspots_v1 test_skirt_yoke_weight_trial_v1 test_skirt_yoke_profile_contract_v1 test_skirt_bounded_research_gate_v1
python3 skirt_yoke_weight_trial_v1.py --input source.glb --actor JuniperOriginal --strength .35 --hip-share .80 --out skirt-yoke-research.glb --receipt yoke.json
```

Use the existing `compute_armhole_chunk_v1.py --index 0..8` and `contact_pose_batch_v1.py` on the derived GLB for a full 73-pose triangle receipt, the existing source-bound `observe_makehuman35_garment_v0.py` for signed 73-frame measures, and `garment_skinned_strain_v1.py` for 72-frame deformation. The compact evidence JSON and `skirt_bounded_research_gate_v1.py` verify the parallel receipts. On a public runner without research scientific dependencies, run only the **17 stdlib hostile source-free cases** from `test_skirt_yoke_profile_contract_v1` and `test_skirt_bounded_research_gate_v1`; the actual source-dependent suites require the exact original-only GLB in owner custody.

Large GLBs, full 73-frame receipts, and PNGs go in owner-private Drive. First-class stdlib source tests, generator code, and a small non-promoting scientific receipt go in the existing public draft PR #336. No new workflow or job is needed.
