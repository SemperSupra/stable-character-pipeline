# R009 — cyclic root-Y floor envelope and phase-window sensitivity (2026-11-07)

**Disposition:** Original-only, source-bound research. New root-Y derivative **PASSES CPU floor/continuity proxies** across REST-absent 72 original animation keys. Native Blender, IK, 3D foot plant, foot pressure/friction, natural gait, body anatomy, wardrobe/cloth, release and CPE **NOT ACCEPTED**.

## Scope and source

- One original fictional Aster/Juniper 35-joint GLB with pinned CC0 MakeHuman human body; SHA256 `b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748`.
- Source-owned original 72-frame sole-correspondence receipt SHA256 `c86d2a6d2ee2f324a3974723fdb2cdc5e29f59d5f033d7414b8e0aaf08409640` and source ankle witness SHA256 `4019fe9a032d66b767a9715500156b4afcdc2df6cd7ddb6293bb0ec682516541` retained privately.
- Public Git contains **only code, hostile tests, scientific compact receipt and this document**; no GLB, original sole-vertex observations, name-bearing real-person inputs, third-party wardrobe, or image renders.

## Batch A — five source-grounded stance/swing sensitivity hypotheses

Ankle world-XZ motion, original shoe min-Y after a *diagnostic* root lift and prior `persistent_vertices>=5` source evidence classify 71 frame transitions per actor/foot as `stance_proxy`, `swing_proxy`, or `ambiguous`. A stance proxy must persist for 2–3 consecutive transitions; singletons are ambiguous. Five sensitivity settings vary ankle-motion and floor-proximity thresholds independently as paired 4/6/8/12 mm, plus an 8 mm, minimum-run 3 scenario. The classifications intentionally do **not** certify plantar pressure, heel/ball/toe contact, a true planted ankle, or a real double-support phase. Original prior ankle-gate false-positive correction remains authoritative.

The five-setting agreement identifies robust candidate intervals and threshold-sensitive transitions for supervised IK trials; it does not automatically derive IK targets. Current source foot-vertex ID tracking is a **count**, not a complete per-vertex identity record; source witness flags that limitation. Reuse the 35-joint leg bones and previous G0 comparison authority. Use sensitivity to prioritize manual/native 72f inspection, not to replace biomechanical criteria.

## Batch B — independently source-verified root-height mathematical foil

Source lower-bound clearance sequence `r_i=-min(sole_L_y,sole_R_y)` from the 72 original Y-up world frames. For a chosen per-frame slope `s=0.002 m`, safety margin `eps=0.0002 m`, cyclic frame distance `d_72(i,j)=min(|i-j|,72-|i-j|)`, the least `s`-Lipschitz upper envelope is:

```
root_lift[i] = max_j (r[j] - s*d_72(i,j)) + eps
```

This mathematically guarantees `root_lift[i] >= r[i]+eps`, circular first/last steps <=2 mm, and circular second differences <=4 mm/frame². Both are below the previous policy budgets of 3 mm/frame and 5 mm/frame². This is a *numerical* root-height feasibility witness, **not** foot-lock or IK.

- **First RED preserved:** initial non-cyclic min-envelope met all 71 interior edges but produced **Juniper frame71→0 jump 3.386 mm**, exceeding the 3 mm policy. Fixed the cyclic geometry, without weakening thresholds; first derivative/receipts remain archived.
- Exact cyclic derivative GLB SHA256 `1ac4c25a501db1a82ce2d729ae4b00d4b6298f673ed5a498f9e4245fa0b87d7d`. CPU re-read of **all 72 frames** confirms zero frames with shoe point below -5 mm, zero both-feet-over-10mm frames, and **+0.200 mm minimum sole height** for both actors. Max root Y step **2 mm** and second difference **4 mm/frame²**, with cyclic boundary included. Character source original BIN prefix, all original accessors, 35-joint skins, body/garment meshes and all non-root animation samplers unchanged. Only two *new* root VEC3 translation accessors selected.
- An independent constant maximum-lift comparator is feasible with zero root-Y step, but adds ~3.6 mm average unnecessary lift; retain as a foil, not adopt.

**Scientific caution:** Numeric Y-up floor clearance with static rigid ground is not sampled continuous-time sweep, sole rotation/heel-toe rocker, planted-foot tangential slip, knee bend, cloth/skin contacts, camera realism or physical pressure. A research CPU `PASS_FLOOR_AND_CONTINUITY_PROXY_ONLY` may be obtained with an unnatural gait. Do not merge/release or claim natural gait from it.

## Source-free hostile gates, repo/DLE custody

The workflow uses the existing source-only R009 synthetic contract job, not another workflow/runner. The two source-free suites cover missing/nonfinite frames, invalid hashes/actors, forged physics acceptance, source mutation, duplicate foot frames, wrong coordinate system, singleton stance, swing false contacts, non-cyclic continuity and fabricated CPU results. Actual original-only GLB integration intentionally **SKIPS** on public GitHub and runs only with owner-admitted original file and `SCP_R009_ORIGINAL_GL_B` + `SCP_R009_ORIGINAL_SOLE` environment variables; no private file download on public runners. Preserve source/rights owner DLE #272 and draft PR #336, with parent #308 base SHA drift HELD. No PR merge/rebase/delete, source GLB overwrite or CPE.

**Next executable:** verify true persistent sole vertex IDs with contact patches (heel/ball/toe), dual support and swing phase under multiple 3D views; author two-bone sagittal leg IK with bounded knee angle, stride, ankle/foot rotations and source-preserving joint constraints; evaluate exact original 72f in native Blender against independent floor and garment BVH, and human visual quality. Track validator false-accept/false-reject performance separately from passing adversarial fixtures.
