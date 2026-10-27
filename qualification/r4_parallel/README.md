# R4 W03 — Bounded parallel public GitHub Actions CPU qualification

Authority: [R4 issue #46](https://github.com/SemperSupra/stable-character-pipeline/issues/46) and [W03 issue #56](https://github.com/SemperSupra/stable-character-pipeline/issues/56). Nested draft workcell on unmerged R4 source admission [PR #54](https://github.com/SemperSupra/stable-character-pipeline/pull/54), **not a release, merge, deploy, CPE concept promotion, or actual learned model inference**.

This is a scoped qualification of the public-runner **concurrency seam**, not an attempt to run all active PRs or duplicate the complete NASA video regression. GitHub-hosted standard runner `ubuntu-24.04`, `max-parallel: 3`, `fail-fast: false`, per-lane timeout 6 minutes, default read-only repository permission, exact PR head checkout, no custom credentials, model/checkpoint/private-media downloads, apt packages, GPU or paid workers. A new commit cancels stale same-PR workflow invocations; **a failing job does not cancel the other two matrix lanes**. Three isolated VMs get the same source SHA but no shared writable workspace.

| Lane | Test | Native evidence | Limit |
| --- | --- | --- | --- |
| `rights` | R4 Go registry/rights positive and adversarial negatives: five models, source media / weights / target rig separate, no forged inference | `r4-parallel-rights` JSON artifact | Source metadata only |
| `adapters` | Model I/O contracts for mesh→skin, photo→body estimate, video+reference rig→motion, photo/video+rig→motion; deny wrong modality/missing independent rights/false identity or 3D claim | `r4-parallel-adapters` JSON artifact | No actual upstream executable import, no weights |
| `synthetic` | Original 3-joint/3-vertex weighted translation-skin CPU fixture, hierarchical transforms, monotonic contiguous source time, missingness/NaN/cycle/skin weight falsifiers | `r4-parallel-synthetic` JSON artifact | No actual Blender import, no anatomical model, no metric 3D |

Commands locally (Go 1.23, no network dependencies): `GO111MODULE=off go test ./qualification/r4_parallel`, `GO111MODULE=off go run qualification/r4_parallel/main.go -lane adapters -manifest qualification/r4_admission/candidates.json -out adapters.json`. Run `rights` and `synthetic` likewise.

**Human UI:** readable table, source/code rights findings, links to individual completed jobs and artifacts in the DLE. **Automation:** exact go test and CLI, independent JSON receipts, checksums, return codes and no shared-state coupling. **Agents:** authority in DLE #56, source SHA, run IDs, which lanes PASS/FAIL, first-failure, and next baton. Stacked PR remains DRAFT, no promotion to product state.

**Important:** standard public GitHub Actions CPU compute is free, but repository-owned artifact storage and fair use/concurrent job limits apply. Larger GPU runners are billed and prohibited. The repository may have other parallel workstreams already active; this workcell does not reorder, merge or cancel those workflows.

**Next if three lanes PASS:** use the generated adapter contract to select source-only, rights-admitted synthetic fixtures for independent third-party rig readers; run a separate deliberately admitted motion/GPU model test only after exact weights, file rights and compute authorization. Independently validate the NASA procedural GLB against native Blender animation in a runner with verified binaries without reinstalling a large apt dependency set. Preserve source rights and release gates.
