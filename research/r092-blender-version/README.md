# R092 Blender migration qualification — no rollout

**Decision under test**: continue pinned 4.5.16 LTS, qualify 5.2.4 LTS as default candidate, run 5.3.0 as feature challenger. Official version references: https://www.blender.org/releases/ ; https://www.blender.org/download/lts/ ; https://www.blender.org/releases/5-3/ .

## Independent free-tier workcells
Three isolated, parallel ubuntu-24.04 public CPU runners: official released Blender 4.5.16 / 5.2.4 / 5.3.0 x64 standalone archives. Each downloads official archive directly, prints full source SHA256, checks actual Blender reported version, then runs original synthetic rig+shape-key+garment proxy Blender animation with saved .blend, independent fresh-process reopen/readback, changing evaluated geometry across 3 frames, and headless still rendering. Only receipts (not scenes, binaries or images) may be uploaded if later explicitly implemented.

This tests *Blender core API and exportable scene behavior only*; it **does not test** MPFB, MakeHuman dressing, actual BVH retargeting, Cycles photoreal, third-party addons, proprietary character identity, native cloth/soft-tissue accuracy, or production source files. Those must run as subsequent exact-archive integration gates before switching the production baseline. Do not silently substitute a different Blender patch version or select 5.3 solely because it passes smoke.

## Release gates (ordered)
1. Evidence: all three version cells run to terminal; retain errors and precise archive hash; no synthetic pass used as MPFB acceptance.
2. Source compatibility: actual MPFB 163-bone dual-actor scene with CC0 garments, fresh Blender-process reopening and source-rights gates, compare 4.5 vs 5.2 and 5.3.
3. Behavior: real R084/R090 shoe contact and skin-deformation numerical critics repeated across versions. No arbitrary acceptance drift.
4. Render: controlled CPU Cycles frames, matched settings; compare image metrics with justified tolerances. Never interpret pixel change as a fidelity improvement without inspecting causes.
5. Workflow promotion: opt-in pin migration to exactly 5.2.4 LTS after passing, keep 4.5.16 rerunnable; 5.3 opt-in only for separately justified features.

## DLE
Durable: commit/head SHA, source archive hash, official download, exact runtime, per-version run and test receipts. Legible: PASS_CORE vs HOLD_M PFB/HOLD_PHYSICS/HOLD_MVP; no silent release claim. Executable: public free-tier independent matrix with CPU budgets and no credentials/paid runners, fail-closed on version or readback mismatch. Original synthetic objects only. Private source authority stays private.
