# PV/Video Physics bakeoff — original Stable Character consumer and portable RDT&E

## Authority and readiness (2026-11-12)
- [Public Visual QA DLE #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150) owns scientific evaluator work. Walking #84 and original R009 #272 are related. Protected-person/identity and product acceptance remain under private authorities. No private character media are admitted to public GHA.
- [Original 22-case corpus PR #369](https://github.com/SemperSupra/stable-character-pipeline/pull/369) is the immutable source-labeled synthetic baseline: 10 targeted geometry/contact PASS, 11 FAIL, 1 UNKNOWN. The 11 must be preserved as negative controls, not silently relabeled.
- The Go CLI is a **research diagnostic** and does not establish natural gait, faithful anatomy, soft-tissue physics, identity, professional martial arts, perceptual excellence, or correct physical contact on arbitrary video.
- PVBench, HumanScore, PhysTrace, RoboJudge, CoTracker3, DOVER, and PyIQA remain independently gated research candidates. Existing upstream-source acquisition does not imply installed/qualified weights, runtime portability, or product approval.

## New actual consumer path — 22 source-bound H.264 files
The `source-bound-video-diagnostics` public Actions job in `.github/workflows/video-expanded-motion-math.yml` reuses the four original, disposable, concurrent corpus-generation jobs. It downloads their exact generated artifacts, verifies the per-video SHA256 against the original generation manifest using `scripts/character_manifest.py`, then runs the existing Go H.264 diagnostic evaluator over the actual bytes.

- `video_eval_cases.json` is **unlabelled**: there is deliberately no `expect` oracle. An unlabelled PASS/FAIL/UNKNOWN is an observed diagnostic verdict, **not** agreement with ground truth.
- The Go CLI preserves the prior labelled synthetic oracles and error-on-oracle-mismatch behavior. Unlabelled observations do not count as matched or mismatched oracles.
- `video_quality_receipts.json` includes input SHA256, actual FFmpeg black/freeze metrics, findings, verdicts, and limitations. Output must include exactly 22 entries with nonempty hash and no decode error before the integration job succeeds.
- The independent existing mathematical audit operates on source skeletons and contact labels and is separate from decoded-frame video diagnostics. These modalities are **not** fused into a realism PASS.
- Rendered original videos are under user-owned Google Drive Motion Corpus RDT&E with direct iPhone H.264 MP4 links. Cloud artifacts are temporary build receipts, not the persistent media archive.
- Do not attempt to download private Drive media or private protected-person characters from public CI. To assess an owner/identity-controlled Stable Character R009 clip, use an admitted private disposable executor and output only approved, redacted receipts.

## Cross-platform workcell
The distinct `video-physics-portable.yml` path-scoped PR workflow builds and executes the **same offline Go source** natively on standard disposable Ubuntu, Windows and macOS GitHub runners. It runs labelled/uncertain/unlabelled JSON motion smoke tests and captures per-platform binary SHA256 and runtime receipts. It tests the Go CLI without FFmpeg, and **does not** qualify native OS-specific H.264 FFmpeg availability, full third-party model stacks, or GPU.

Local research use if the tools are already provisioned in a disposable environment:

```sh
cd qualification/video_physics_bakeoff
GOWORK=off GOPROXY=off GOSUMDB=off go test ./...
GOWORK=off GOPROXY=off GOSUMDB=off go build -trimpath -o bakeoff ./cmd/bakeoff
# Given synthetic rights-cleared local corpus videos generated as four batch folders:
python3 scripts/character_manifest.py --root ../expanded_motion_corpus/runs --out ../expanded_motion_corpus/runs/video_eval_cases.json
./bakeoff -manifest ../expanded_motion_corpus/runs/video_eval_cases.json -out ../expanded_motion_corpus/runs/video_quality_receipts.json
```

On Windows use `bakeoff.exe` and a PowerShell-compatible environment; FFmpeg and FFprobe must be discoverable on PATH for video evaluation. The corpus generator itself is Python+OpenCV+NumPy and currently cloud-Linux-qualified, not separately native-tested on Windows/macOS.

## Required statelessness and promotion gates
1. **Cloud:** standard public Actions VM is destroyed after each job; use only rights-original synthetic fixtures in public jobs. Go modules are stdlib-only; any acquired FFmpeg or model dependencies live on the temporary runner. All cloud artifacts must have bounded retention.
2. **Local Windows/macOS/Linux:** run in a throwaway VM or container with read-only input mount and separately mounted writable output; do not install Go, FFmpeg, Python dependencies, checkpoints, or package caches directly on a persistent host as a prerequisite. A disposable project `.local` or `~/.local` fallback is permissible when scoped and cleaned up; not preferred. If no admitted disposable runtime exists, report **NOT_QUALIFIED**.
3. **Deployment:** no production OCI image, signed native installers, Windows/macOS H.264 runtime qualification, or multi-arch container verification exists from this branch yet. Build provenance, artifact hashes, pinned bases, read-only root filesystem, and ephemeral state remain gating work.
4. **Scientific bakeoff:** actual pretrained CoTracker3 CPU checkerboard inference exists as a separate draft research workcell, not demonstrated on all 22 character MP4s. PVBench is a candidate research methodology/tool, not a synonym for the local Go bakeoff or evidence that its full checkpoint suite has been installed.
5. **Three audiences:** JSON receipts support automation and agents. Human/assistive review should use the existing QA UI and iPhone media index. This workcell does not replace or modify the actor-owned annotation UI, which still needs its own acceptance and accessible theme mode controls.

No merge, release, product acceptance, public person media exposure, or paid/cloud GPU spend is authorized by this workcell. Record source SHA, native workflow/job/artifact receipts, scientific failures and outstanding holds in the DLE before promoting any claim.
