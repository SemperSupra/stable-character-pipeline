# Video physics QA: independent $0 RDT&E qualification

**Authority:** [public visual QA #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), [public original R009 #272](https://github.com/SemperSupra/stable-character-pipeline/issues/272). [Protected private #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23) remains the product acceptance authority. This workcell neither owns nor modifies the actor-owned QA UI.

## Goals

- Compare traditional decoded-video checks and source-observed motion against deliberately clean, corrupted and ambiguous synthetic cases.
- Acquire upstream research tools into fresh disposable workers at immutable commits (not mutable branches).
- Distinguish source obtained, dependencies installed, weights obtained, inference observed, accuracy qualified, and product accepted.
- Feed timestamped, source-bound metric receipts to the existing human/automation/agent QA interface without assuming an LLM judge is ground truth.

## Clean-room CPU replay

Requirements: disposable Linux worker with Go 1.23+, FFmpeg, FFprobe, libx264, Git and Python 3 (for source inventory). The included public Actions workflow provides a fresh `ubuntu-24.04` VM and checks installed tools. No persistent workstation configuration, secret, paid GPU, or vendor media is needed.

```bash
cd qualification/video_physics_bakeoff
GOWORK=off GOPROXY=off GOSUMDB=off go test ./...
bash scripts/generate-videos.sh
mkdir -p results
GOWORK=off GOPROXY=off GOSUMDB=off go run ./cmd/bakeoff -manifest fixtures/cases.json -out results/baseline.json
```

The seven oracle cases include a clean planted foot (PASS), planted-foot sliding (FAIL), missing contact evidence (UNKNOWN), clean moving video (PASS), unexpectedly frozen video (FAIL), black video (FAIL), and intentionally ambiguous static video (UNKNOWN). The metric thresholds are **research hypotheses**, not calibrated standards. The output receipt records input SHA256, metrics, defects and distinctions between FAIL and UNKNOWN. The synthetic-only test does not qualify realistic anatomy, natural gait or actual-human assets.

## Upstream research models

Pinned commits: [sources.tsv](sources.tsv). Each candidate is acquired in a fresh throwaway directory using `scripts/acquire-source.sh`; this only fetches first-party repo files, does not run upstream code, install dependencies, download Git LFS, gated checkpoints, weights or perform inference. GitHub Actions runs seven source probes independently. Source pin receipt means **SOURCE_ACQUIRED only**; it is never a claim of model installation or quality.

| Candidate | Research role | Deferred installation/weights gate |
|---|---|---|
| HumanScore | biomechanics, human gait | SMPL-X licensed/gated body model, 25 GB disk, >=16 GB NVIDIA GPU |
| PhysTrace | temporal physics localization | verified dependencies and checkpoint pin |
| PVBench | numerical physics evaluation | specialist models, checkpoints and high-memory Qwen |
| RoboJudge | perception-based physics judge | pinned Hugging Face 9B weight files and GPU |
| CoTracker3 | pixel tracking | independently pinned checkpoint, CPU/GPU pilot |
| DOVER | perceptual video quality | dependency and checkpoint audit |
| PyIQA | image-quality metrics | image-only pilot, no motion claim |

Research-only/noncommercial licensing is allowed for these **RDT&E** candidates when the specific permission and access conditions are met. The eventual production/redistribution transition remains separately gated. Standard public GitHub runners supply 4 CPU/16 GB RAM/14 GB SSD, **not an assumed GPU**. HumanScore's documented ~25 GB disk requirement cannot fit that runner. No unqualified large weight downloads are attempted.

## Next experiments

1. Validate SOURCE_ACQUIRED receipts from actual native Actions runs. Preserve first source-fetch failures.
2. Compare deterministic scores, timing, accuracy and false positives on adversarial clips and calibrated source-trace witnesses.
3. In disposable isolated environments, build/install selected models and record dependency trees, license, rights and model OIDs. No permanent host installs.
4. Only after an observed no-charge GPU admission, run actual model inference on the same rights-cleared test clips and measure VRAM, runtime and incremental detector value.
5. Run bounded corrective A/B tests: localized defect -> fix proposal -> regenerated candidate -> independent objective retest -> regression and rollback evidence.

**No merges, releases, protected asset publication, CPE promotion or product acceptance are authorized by this research branch.** Source and compact receipts belong in Git/DLE; large rights-cleared artifacts belong in existing external custody with SHA readback.
