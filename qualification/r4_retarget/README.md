# R4 W04 — source-only synthetic motion retarget between two nonidentical rigs

Authority: [R4 W04 DLE #69](https://github.com/SemperSupra/stable-character-pipeline/issues/69), source/model/target rights owner [R4 #46](https://github.com/SemperSupra/stable-character-pipeline/issues/46), previous [R4 W03 #56](https://github.com/SemperSupra/stable-character-pipeline/issues/56). Independent research-only. Not a production human body, animal skeleton, Mixamo import or learned model inference.

## Actual experiment

Four original synthetic camera-plane local joints (root, hip, knee, ankle) map onto a separate four-joint robot-like reference rig (base, pivot, hinge, tip). Rig topology is different in length proportions but joint ancestry must be one-to-one and preserved. The `map` lane rejects duplicates, cycles, roots, missing mappings, incorrect parent relationships, provenance mismatches, attempted metric-depth claims, NaN and zero-length bones.

The `motion` lane accepts three original synthetic samples at source 0/1000/2000 ms, scales local translation delta by declared target/source rest segment length. At t=2 the source knee moves 0.2 arbitrary camera-plane units; target segment/source segment = 0.4/0.8, so target knee moves 0.1 units. Negative cases reject invisible/missing/nonfinite joints, invented depth, missing source time, silent interpolation and unauthorized model modes. No quaternion, IK, physics, learned rigging or human likeness claim.

## Operational contract

One Go 1.23 standard-library CLI, `-lane map|motion -out path`, deterministic JSON receipt and fail-closed exit. Two independent read-only standard public GitHub Actions CPUs with `max-parallel:2`, `fail-fast:false`, 7-minute budget and per-lane machine artifacts. No model/media/source downloads, paid/private runners or GPU. Distinct source, checkpoint, reference rig and output rights persist from R4.

Human UI: mapping/readable limitations and public Actions logs. Automation: Go CLI/JSON/return codes. Agent: exact PR/head, job and artifact IDs in DLE #69 plus next bounded action. No unapproved publication or accepted model inference.

## Next dependency gates

Native Blender import of mapped target skeleton and correct procedural deformation; full quaternion and joint-local transform/coordinate/timebase proof; independent ankle contact and IK falsifiers; rights admission for any real media/model/rig and appropriate private execution. Research-only DRAFT; no merge/release/deploy/CPE promotion.