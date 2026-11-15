# R033 free public-runner vision baseline (research only)

Independent CPU workcell for Stable Character R033, with methods crossfed to Oneirifact critic flywheel R60. No Oneirifact/private source, real human identity or protected photos are ever transmitted. Uses two original synthetic PNGs of red circles; correctness labels are independently known by construction.

- Model: `HuggingFaceTB/SmolVLM-256M-Instruct`, exact upstream revision `d039ab0d4b9311b617e8ffec1d06c8464364aeb3`, publisher model card claims Apache-2.0. Run from safetensors with `trust_remote_code=False`.
- CPU only on public standard GitHub-hosted Ubuntu, bounded job timeout 17min, no secrets, no paid remote API and no weight artifact retention. Dependencies pinned to named versions.
- Metric is extremely narrow red-circle count on two **first-party generated** PNGs; poor model outputs are RED/UNKNOWN, not silently repaired by string tests. No claim of calibrated multi-view 3D anatomical/photoreal/motion review or automatic generator acceptance.
- Go core/edit scheduling remains in Oneirifact; this experiment only emits typed evidence for evaluating a potential replaceable critic adapter.
- If package download, host, model weights, or CPU timeout fails, preserve first-failure run and report `UNQUALIFIED`. No unbounded retries or paid fallback.
- No real personal faces, user preference, restricted model sources, or remote cloud VLM call. Review source and license notices before any production adoption.

Workset authorities: `SemperSupra/stable-character-pipeline-private#168`, `SemperSupra/oneirifact-private#88`. No change to protected G4/G5 or R009 release.
