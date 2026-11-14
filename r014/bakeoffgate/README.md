# R014 native-MHR corrective bake-off admission (research draft)

This independent public-safe **source-only** gate addresses private engineering DLE #138 and Product DLE #2: do not attribute CMU07/MHR lower-leg collapse to missing neural correctives until a controlled native-vs-Blender differential exists. It does **not** execute MHR, prove any license, clear a geometry gate, or select a canonical CharacterPack.

## Experiment plan

Use each complete source clip (CMU07_01 64 frames; held-out CMU07_02 66 frames) against four matched evaluation arms:

1. MHR native, pose-dependent correctives OFF
2. MHR native, pose-dependent correctives ON
3. Blender imported armature, linear skinning
4. Blender imported armature, Preserve Volume

First prove the source model weights, joint pose parameterization, exact **127 native vs 126 imported joint** semantics, topology correspondence, rest/bind reference, calibration, and ground-snap behavior. All arms for one clip must share the same pinned source pose stream, model, crosswalks, rest pose and unit calibration; force root ground snap OFF. Reject missing frames or unmatched snapshots, not just count tests as green.

Collect per-frame numerical **area ratios (rest and first captured frame separately), edge strain, local hinge opposition, actual self-intersection checks, knee/ankle/toe residuals, and contact provenance**. Preserve historical collapsed-face, r_lowleg/root, source-knee and ankle trade-offs; do not turn normal reversals into a proof of self-intersection. For exact-source native MHR, also record apply_correctives and model/activation-asset hashes, LOD and source pose-space conventions.

Source inputs require **independently reviewed, per-artifact/per-operation/per-venue** grants (model weights, each motion clip, joint and topology crosswalks, calibration, rest pose). The input plan cannot grant itself rights. This prototype takes a caller-supplied trusted registry; it does not verify authenticity of that registry. In particular, non-commercial RDTE is not a blanket license, local rights do not authorize a private GHA runner, and protected sources must never be staged in public CI. No hidden vendor weights, reference video, actor identity or model data are included in this branch.

The synthetic-only fixture exercises the contract and adversarial failures. The resulting status READY_TO_EXECUTE_RESEARCH_ONLY__NO_QUALITY_OR_RELEASE_PASS is **plan-validity only**, not measured geometry PASS or permission from the model licensor. A separate independently signed execution/rights record is required for real donor tests.

## Reproduce

From r014/bakeoffgate run go test -race -count=1 -v ./..., go vet ./..., and go run ./cmd/receipt.

The workflow uses a public/free runner, read-only checkout without credentials, short job timeout, pinned action SHAs and short-lived JSON-only source-safe receipt. Non-code evidence belongs in the existing private R014 Drive folder, with ZIP SHA256 rehydration, not committed to Git. This PR stays DRAFT; no merging, private minutes, deployment, source transfer, canon or release.
