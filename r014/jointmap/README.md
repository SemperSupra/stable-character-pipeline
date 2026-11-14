# R014 W1 native MHR to Blender joint-space structural falsifier

This independent **research-only, source-safe** Go workcell defines a falsifiable joint mapping contract for the 127-joint upstream native MHR model and the 126-bone Blender MHR import reported in R014. This is an **assumption-under-test**: one missing global/nondeforming joint is NOT an established explanation for the difference. A real native/source asset could require a different adapter, multiple collapsed relations, or a non-bijective semantic mapping. This workcell must reject or abstain rather than assert a false one-to-one model.

## Direct pinned source observations

Official upstream at inspected main blob pins:
- `facebookresearch/MHR/mhr/mhr.py`: Git blob `28f2e57b00f98ca63a32315d45d10c2fc49aee8f`; in `MHRPoseCorrectivesModel._pose_features_from_joint_params`, the first two global joints are excluded, and remaining local Euler rotations are converted to centered six-dimensional rotation features; in `MHR.forward`, correctives are added to rest vertices before skin_points.
- `facebookresearch/MHR/mhr/io.py`: Git blob `8325a469edc6c00dd317d8320fc0c29e52fb57dc`; the first pose-corrective layer takes `125 * 6` features, has `125 * 24` outputs, and feeds a corrective blendshape projection. Required model components include `compact_v6_1.model`, `lod?.fbx`, `corrective_activation.npz` and `corrective_blendshapes_lod?.npz`.
- Current R014 imported Blender retargeter `r014/mhr_cmu07_native_walk_retarget.py`: blob `f29e6e3b54cdcc5a2ba41543fdefa7e39a499564` at original motion PR #486 head, checks 126 imported bones and 18,439 vertices, scales imported armature world basis by 0.01, and does not call the MHR native neural corrective inference in the inspected script.

**Do not infer:** those two excluded native feature joints correspond to one missing Blender bone; any one specific global node has been dropped; a Blender unit is one metre; an original imported FBX bone tail represents the anatomical joint; or a proper rigid rotation is a skin foldover. No native model weights were loaded or native-to-imported match proven in this workcell.

## Directly source-inspected native extraction route

The official MHR viewer `web-viewer/server.py`, pinned Git blob `8ac3f34585278d2e0d0fc7412ae1542613439109`, loads the TorchScript model with `torch.jit.load(..., map_location="cpu")`; `MHREngine.__init__` reads `self.model.get_joint_names()` and `self.model.character_torch.skeleton.joint_parents`. Its configuration exposes `jointNames` and `jointParents`. It also reads `get_lbsw()`, so a validated source-native witness can distinguish nominal skeleton nodes from actual vertex influences rather than assuming any excluded joint is nondeforming.

The same viewer divides `skeleton[:, :3]` by 100 for its visualization export. The inspected imported Blender R014 script records the FBX rig `matrix_world` scale of 0.01. Those are **two observed implementation conventions**, not an automatically proven physical centimeter↔metre or joint-space parity. The real W1 extractor must report exact model, LOD, native TorchScript, asset/license/version SHA, source and Blender object/world/rest transforms, joint names/parent IDs, and LBS per-joint influence. Suppress source-native full geometry or detailed protected identifiers from public artifacts pending operation/venue rights.

Upstream `v1.0.1` GitHub release metadata lists a 198,943,157-byte `assets.zip` published 2025-11-19 and notes “Added LICENSE to assets.” That release note does not substitute for inspecting the actual archive-embedded license and any separately supplied terms. This workcell did **not** download it.

## Strict structural gate

With source-byte SHA pins and a genuinely independently reviewed mapping/omission registry, the validator requires:
- 127 unique native joints and 126 unique imported joints, exactly one explicit nondeforming omission with independent proof and a SHA-bound 126-pair bijection.
- Acyclic one-root skeleton graphs; each imported parent edge matches the corresponding native ancestry after the explicit omission; matching left/right/center annotations.
- Finite rest positions and a source-to-target 3D proper orthogonal rotation (no reflection or shear), positive scale, independently attested calibration SHA and rest residual tolerance, bounded residuals for all 126 matched joints.
- Versioned native and Blender local-pose conventions and explicit source-rights UNKNOWN, regardless of structurally passing checks.
- The outside trusted registry is **not** automatically authenticated by this package: machine receipts still require independently pinned source bytes, source terms and venue/operation grants. A mapping presented by a candidate cannot be its own independent proof.

The synthetic fixture uses a fictional 127-node chain; it intentionally does NOT enumerate MHR joints. Passing means only that the **structural contract works on synthetic controls**. The actual MHR joint-map result, animation and photoreal acceptance remain UNKNOWN/HOLD. Under the non-commercial RDTE policy, no model/weight, actor, CMU original media, private scene or facial asset enters public GHA.

## Follow-on real-source rep (not performed here)

1. Admit and hash exact native MHR `compact_v6_1.model`, LOD FBX and neural corrective assets for an approved venue and operation. Establish valid native extraction of joint names, parents, rest-state transforms and deform status.
2. Independently extract matching imported Blender armature rest names, parents, object/world matrices, parent inversion, basis conversion and source hashes from a cold-reopened saved scene.
3. Test whether the hypothesized exactly-one-omitted-joint bijection is structurally possible; if not, report FAIL and design a typed many-to-one/virtual-joint adapter instead of forcing a map.
4. Compare source coordinate conventions, source pose-to-skin mapping, units, rest alignment, ground snap and first source motion frame. Only then run #501 corrective ON/OFF versus Blender four-arm dual-clip differential.

All R014 skin/knee/contact, R015 measured morphology, product D1–D4, R009 rights/film and release gates remain HOLD. Keep draft/unmerged and independent of PR #501, #486, #490, #492, #498, #499.
