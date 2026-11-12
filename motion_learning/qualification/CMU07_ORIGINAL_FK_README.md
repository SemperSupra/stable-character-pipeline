# Motion S2 — Original measured CMU07 walking source 3D FK qualification

**Source ownership:** Shared motion source index [public #29](https://github.com/SemperSupra/stable-character-pipeline/issues/29), established multilingual source research [#349](https://github.com/SemperSupra/stable-character-pipeline/issues/349), MMD/source adapters [#19](https://github.com/SemperSupra/stable-character-pipeline/issues/19), canonical W07 Go [#84](https://github.com/SemperSupra/stable-character-pipeline/issues/84); original human source authority remains protected R012 [private #35](https://github.com/SemperSupra/stable-character-pipeline-private/issues/35). R014 private #138 is a future rig/skin **consumer**, not motion-data owner.

## Reproduce exact source

This is stacked atop source-only [CMU S0/S1 draft #468](https://github.com/SemperSupra/stable-character-pipeline/pull/468). Two independent free public GitHub Actions Ubuntu workers, no private GHA or protected model/identity, re-download directly from original official CMU subject 07 publisher via **verified TLS**, repairing the publisher's incomplete intermediate chain with **official HTTPS Let's Encrypt YE1 chain certificates** and verifying leaf to original OS trust roots. A source SHA mismatch aborts before FK:

- Original calibrated `07.asf` source bytes SHA-256 `c29414591d76a34885bff0b04a2666bf9659f869751a2549591c55277cf95b04`
- Original `07_01.amc` SHA-256 `3ca8e8b834481c97c32e9dd555f8c9023e33b6c52d93c9d556c83570204bf3f2`
- Original `07_02.amc` SHA-256 `a6062c6c6bce037241d345ca8d802ab36a5cf003b60f759aa7b1db545219c065`

Original source files **never leave the disposable CI runtime**; published artifact contains only per-source metadata and a three-timepoint sparse joint sample plus aggregate speed and toe-height statistics. No raw ASF/AMC or complete derived measured trajectory; no rights conversion or anonymous re-identification. CMU publisher allows many reuse cases but forbids direct resale of capture data/converted form; exact downstream transfer and training admission remain separate.

## Real original skeleton and FK

Pin source review code `CalciferZh/AMCParser@08e5a3662e197e7e40eed2c18fc254282eb381f9` (MIT source) in disposable Python venv; use its ASF joint hierarchy, DOF and AMC rotations to compute **every observed frame** of original joint positions. Independently validate all 30 ASF segment lengths against the original calibrated source geometry, original root AMC coordinates and actual source published metric factor `(1/0.45)*2.54/100`. Source AMC 120Hz is publisher-declared clock, not separately measured camera frame cadence.

Actual independent [GHA 43323993856](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43323993856) finished two jobs SUCCESS:

| Recording | Frames | Root end-to-end position difference | Measured left toe p95 instantaneous speed | Measured right toe p95 instantaneous speed | Max segment length residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| `07_01.amc` | 316 | 3.58277232m | 4.71780056m/s | 4.40216983m/s | 2.507e-16m |
| `07_02.amc` | 329 | 3.62672338m | 4.60158649m/s | 4.27352243m/s | 2.507e-16m |

There are 29 animated joint channels plus root; original ASF defines 30 body bones. The source joint velocity values may reflect rapid swing, sampling noise, coordinate-space or toolchain assumptions and **DO NOT imply physical pressure, observed foot contact or natural locomotion**. Source left/right toe Y-extents, first/mid/last source FK world positions and speed percentiles are preserved for independent analysis. The current authoring framework trusts one pinned open-source FK parser and validates bone lengths and raw root. A second differently implemented FK engine has not compared all joint positions yet.

**Explicit research status:** `PASS_ORIGINAL_SOURCE_FK_STRUCTURAL_METADATA_ONLY`; **NOT** true measured heel/sole contact, full-body MHR/MPFB retarget, anatomy-safe gait, natural video, and especially **not** photoreal cinematic human qualification. Need source correspondence, rest coordinate bases, original ground plane, time-domain and contact confidence, source-to-target stride adaptation and native Blender witness. The existing [R014 source-model gait #463](https://github.com/SemperSupra/stable-character-pipeline/pull/463) remains a synthetic Go baseline to compare, not a substitute for CMU measured walking; R014 toe corrective #467 remains HOLD due five skin inversions.

All source changes remain draft and unmerged; public main and private R009 protected media are untouched.