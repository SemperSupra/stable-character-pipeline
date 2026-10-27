# W01 — Four original public workstreams in parallel (source-only)
Owner: [public DLE #60](https://github.com/SemperSupra/stable-character-pipeline/issues/60). This qualification is a new orchestrator-only draft based on the public repository's main; it does not change or promote any of its source PRs.

**Why:** [R4 W03 public three-way qualification](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40594778575) already proved independent `max-parallel:3` CPU scheduling with separate Go source rights, adapter and synthetic skin receipts. Four other candidate PRs have independently authored Go tests that can run without model weights, private inputs or slow Blender/apt installs.

## Immutable public sources
| Lane | Owning PR/DLE | Exact source revision | What the test can prove |
| --- | --- | --- | --- |
| motion | [PR #31](https://github.com/SemperSupra/stable-character-pipeline/pull/31) / issue #29 | `278fdf54c0938dd508c0361fd0dc80e72a3fe2f0` | synthetic ASF/AMC format/rights, no FK, no real motion |
| fauna | [PR #32](https://github.com/SemperSupra/stable-character-pipeline/pull/32) / issue #5 | `6c6f1a368d96e059a6689cae8fc7c73900a0bbcb` | 7×3 synthetic horse CSV parsing/native layout and heuristic contact uncertainties |
| mmd | [PR #30](https://github.com/SemperSupra/stable-character-pipeline/pull/30) / issue #19 | `4d7a125574e9328c925745875fd1bdb9eee70c4f` | typed evidence envelope structural validation, not actual Blender MMD animation |
| spatial | [PR #50](https://github.com/SemperSupra/stable-character-pipeline/pull/50) / issue #39 | `8b5b02ab9575475efb6a963ead7302c0cec414dd` | 42 candidate 3D ENU source positions and unmeasured native PCM status |

The matrix checkout is the exact 40-character hash rather than a moving PR branch. If one PR updates, **this experiment remains pinned and is not a claim about that newer revision**; refresh DLE and create a new reviewed workcell for source changes.

## Operational architecture
The workflow `.github/workflows/portfolio-w01-fourway.yml` uses four distinct GitHub-hosted standard `ubuntu-24.04` public CPU VMs. `max-parallel:4`, `fail-fast:false`, `timeout-minutes:9` and read-only `contents:read`. No repositories or source blobs are altered by any lane, no paid/large runners or extra credentials, no 3rd-party character or real motion data. Go 1.23 local stdlib adapters with normal project-only module resolution; the original tests use `-race` and `go vet`.

- Human: GitHub run page shows four independent job statuses, each own source and narrow classification.
- Automation: each job writes `native-proof.json` (plus fauna's `native-header-proof.json`) and source-pinned `portfolio-w01-receipt.json` with SHA256s.
- Agent: DLE #60 records exact orchestrator head and each native job ID, first failure, actions/artifact IDs and baton.

**Status semantics:** run success is not a merged release, a new rigging model, verified real-world animal contacts, a physically accurate 3D reconstruction, a Blender render or perceptual spatial engine audio. Keep these independently held. GitHub Actions artifacts are convenience evidence (3 days), whereas the source and DLE receipts are the long-lived authority.

**Admission:** no private assets or source secrets, no GPU, no learned model downloads/inferences, no deployments/merges/releases, no CPE promotion. Any new claim requires owner authority and separate proof. Existing MMD, fauna, motion, audio and NASA R5 workflows continue independently; this pass does not automatically dispatch or cancel their workstreams.
