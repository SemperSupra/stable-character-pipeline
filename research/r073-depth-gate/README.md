# R073 — hard depth/source-witness gate, independent source-only corrective action

**Existing authority:** R070 [draft #615](https://github.com/SemperSupra/stable-character-pipeline/pull/615) limited 2D similarity, R072 [draft #617](https://github.com/SemperSupra/stable-character-pipeline/pull/617) 3D parallax falsification, public [Visual QA #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), private [R033 #168](https://github.com/SemperSupra/stable-character-pipeline-private/issues/168), private [R009 MVP #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23). New stacked DRAFT, no protected owner branch edit; DLE = Durable, Legible, Executable.

R072 actual decoded H264 tests proved a stationary subject at different depth can be labeled moving by R070 (near Z2 LEFT -18px, far Z8 RIGHT +9px) even when R070 returned `PASS_NARROW_SOURCE_ONLY`. Rather than suppress those red findings, R073 prototypes a **typed fail-closed consumer gate**.

## Admission rules and evidence
R073 consumes the exact R070 decoded-frame observation receipt **and** R072 independent original 3D-world source receipt, with a separately read exact decoded-frame SHA pair and source commit SHA. Bounded JSON parser rejects duplicate keys (including nested), unknown fields, trailing data, oversized receipts and mismatched schema/source/scene/frame identities. It uses a deliberately **fixed, listed original synthetic world scene catalog**: world subject motion, subject Z, nearest reference Z, scene class, expected world truth must agree with independently received witness fields.

It will return **successful CLI exit only for** `ADMIT_SYNTHETIC_COPLANAR_ONLY`: source-proven, exact-matched frames, known original coplanar camera scenario and correct world-direction observation. Every other combination **must exit nonzero with a typed HOLD**:
- `HOLD_PARALLAX`: near/far stationary depth mismatch, even when R070 falsely claims success
- `HOLD_REFERENCE_DEPTH`: inconsistent static fiducial depths
- `HOLD_MISSING_SUBJECT`: no second frame red witness
- `HOLD_PROJECTIVE_CAMERA`: camera yaw outside 2D similarity assumptions
- `HOLD_UNVERIFIED_EVIDENCE`: no exact source/frame SHA, conflicting labels/scene truth, missing/forged world metadata, duplicate/trailing/unknown JSON
- Fail-closed even for a forged claim of a previously safe mode; no undeclared scene or implicit "unknown means pass"

Eight independent public CPU GHA jobs **re-run actual original 3D pinhole→H264 encode/decode→unmodified R070 2D critic→independent R072 world critique→R073 typed consumer admission**. Go 1.23 offline race/vet, hostile tampering unit tests, frame/model witness SHA read from actual files and logs; no image/video asset upload, 3-day receipts. Negative cases are successful only if the *application exits nonzero and the expected HOLD code is present*, not if defects are silently ignored.

**Scope warning:** This is an original-**synthetic-only** fixture admission gate with trusted typed world truth supplied by its pinned generator. It is **NOT** cryptographically authenticating external/protected model assets, dynamic rig topology/identity, full 3D motion, native camera calibration, arbitrary footage or actual source provenance. A user-submitted copy of a fixture receipt without external issuer/security cannot be trusted as production source. For production, require authenticated source-native scene/rig/camera provenance, rights, temporal hashes, and separately qualified depth/witness measurement; otherwise all motion labels HOLD. No new scheduler, paid API, private GHA minutes, protected identity media, automatic merge/deploy/release or owner gate relaxation.

At creation **NOT_OBSERVED** until exact hosted job receipts. Results must crossfeed existing DLE with actual first REDs; neither tests nor 8/8 CI constitute film acceptance.
