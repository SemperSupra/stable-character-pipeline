# Fauna W1 — seven-landmark synthetic horse CSV source/observation qualification

**Authority:** [fauna #5](https://github.com/SemperSupra/stable-character-pipeline/issues/5#issuecomment-6442030639); shared motion-training [coordination #29](https://github.com/SemperSupra/stable-character-pipeline/issues/29). This branch is an isolated candidate stacked on synthetic motion PR #24. It does not rewrite the separate fauna rig/contact PR #26 or human ASF/AMC PR #31.

## Evidence-based primitive choice

The public, pinned [Kine2Go horse source adapter](https://github.com/nomagiclab/kine2go-pipeline/blob/65b39f104706c1b4307dfc2a7df2aa8bed8d20aa/motion_retargeting/datasets/horse.py) reads *timestamp CSV column 1* and columns 2–22 as **21 positions = seven XYZ landmarks** (Head, Withers, Sacrum, HFL, HFR, HHL, HHR). Its `z < 15` contact check, smoothing penalty and 0.00025 scaling belong to *its own estimated motion pipeline*; they are not evidence of independently measured contact or calibrated physical units. This W1 experiment **does not clone Kine2Go or reuse its data**. It reproduces only the 7×3 observation interface with an **original synthetic file**, Go standard library code, and three independently chosen source-unit thresholds. The later actual VHDC file would require a separate adapter after reading original headers/terms.

**Rights hold:** official VHDC source describes **CC BY-SA 3.0 Unported**; Kine2Go's copied Horse folder calls it **CC BY-SA 4.0**. Neither GPL/BSD tool licenses nor our self-authored fake CSV entitle a third-party horse-data transfer, model training or redistribution. `NOT_ADMITTED` is mandatory.

## Honest data contract

The synthetic CSV explicitly self-identifies using the marker `SCP_ORIGINAL_SYNTHETIC_HORSE_CSV_V1` and has 23 columns: marker/frame index 0, a `timestamp_s` column 1, and seven named 3-vector point channels in columns 2..22. The provenance marker is a *test-scope guard*, **not an authenticity or rights signature**. The CSV is hand-authored, four frames, intentionally arbitrary units. A different real VHDC layout or units must fail, not be coerced.

Outputs: exact source SHA256, explicit source ID/family, original synthetic numeric XYZ observations, timestamp samples, `physical_meters_per_unit:null`, `relative_or_global:UNKNOWN`, `native_fps:UNKNOWN`, zero claimed observed ground contact or ground plane and `admission:NOT_ADMITTED`. No 17-joint horse rig, anatomical ground truth, kinetic forces, global root, true gait labels or physical floor is computed.

`Falsify` compares three arbitrary **source-unit** hoof-height thresholds (`0.08, 0.12, 0.20`) and counts how many inferred below-threshold contact flags change. These flags remain **HEURISTIC**, not source-observed. It reparses the original bytes and requires exact observation equality, so an attacker cannot claim a genuine hash but replace landmark heights or claim physical contact.

The split check groups by **horse identity, recording family and derivative family**, independent of marker set (M1/M2/M3). Any split change for the same horse or recording is rejected. This is intentionally strict for the first small VHDC candidate and may reduce independent train/test count: lack of independent horses is a dataset limitation, not permission to split related recordings.

## Three audiences and $0 reproducibility

Human: read the original synthetic fixture, generated JSON receipt, threshold decision changes and unknown/held claims, including SHA manifest and first failures. Automation: `cd motion_learning/fauna_csv && go test -race -count=1 ./... && go vet ./... && go run ./cmd/inspect -source testdata/original.synthetic-horse.csv -source-id synthetic:horse1:walk1 -capture-family synthetic:horse1:sessionA -out /tmp/horse-report.json`. Agent: the exact same machine JSON contract, CLI and source hash; no hidden database, no auto-admission API. Interactive audience interfaces and actual actor qualification remain unimplemented.

Dedicated public workflow [motion-fauna-seven-landmark.yml](../../.github/workflows/motion-fauna-seven-landmark.yml) runs the Go parser/test/CLI, an **independent Python standard-library CSV crosscheck** of numerical coordinates, source hash, thresholds and source-vs-inferred status, rejects marker spoofing and tampered provenance, and publishes only this original synthetic JSON/source digest with a 14-day receipt. An independent parser reading a *synthetic* CSV is not a second observed animal source.

## Known gaps / next baton

The original VHDC `Horse1_M1_walk1_kinematics.csv` was **not read** and its original headers/time/coordinate units/file hash were not verified. The original VHDC license version and any conditions for derived training/model weights remain unresolved. Kine2Go's root optimization and scale require a separate controlled parametric A/B and accepted data/physics oracle; foot z thresholds cannot establish hard contact. A real source file cannot be substituted for the synthetic fixture or uploaded to Kaggle until original source/rights/file SHA and executor admission are complete. No merge, deployment, release, policy promotion or TPU/GPU hardware use is authorized by this workcell.

## W2 source-native shape, licensing layers and timing (read-only scope)

A separate Go `native_layout.go` + CLI `cmd/nativeprobe` now recognizes the **actual pinned third-party copy header shape**, not the earlier fabricated test header: `"Frame#","Time","HeadX","HeadY","HeadZ",...,"HHRX","HHRY","HHRZ"`. Verified upstream source reference: [Horse1_M1_walk1_kinematics.csv @ 65b39f1](https://github.com/nomagiclab/kine2go-pipeline/blob/65b39f104706c1b4307dfc2a7df2aa8bed8d20aa/motion_retargeting/data/Horse/Horse1_M1_walk1_kinematics.csv), Git **blob** SHA1 `28ba2b8b744dc50c52ee6bdffaa4dabca5fd9ad3` (NOT an original-host file SHA256). Upstream copied-file opening rows show frame 1,2,3 and numeric `Time` values 0.000, 0.017, 0.033. This is observed *in the third-party GitHub copy*, not original VHDC-host custody. Sample numeric times are not sufficient to assert a file native frame rate or time unit.

The new read-only Go probe takes `-expected-sha256` and returns source digest, field order, first/last 1-based frames, monotonic time-number extrema and delta range. **A digest supplied by the same caller is only an integrity consistency check, not independent data-authority proof**. The JSON explicitly retains `dataset_admission:NOT_ADMITTED`, `physical_units:UNKNOWN`, `source_time_unit:UNKNOWN`, `native_fps:UNKNOWN`, `relative_or_global:UNKNOWN` and denies claims of captured source-host equivalence or physical contact. It does not serialize landmark values, perform root fitting, infer hoof contact or upload original horse files.

The workflow runs this probe against a *different new self-authored* five-row synthetic CSV **matching the real header and one-based frame layout**. The independent Python CSV oracle checks time increments `[0.017,0.016,0.017,0.017]`, source hashes and six unpromoted source/rights/physics flags. Red controls reject malformed native header/time/XYZ, wrong supplied digest, and the older fabricated synthetic-marker header even when its bytes are correctly hashed. Existing source-marker synthetic contact sensitivity experiment runs independently. Reproduce headless in the Go module:

```sh
cd motion_learning/fauna_csv
go test -race -count=1 ./...
go vet ./...
source=testdata/original.synthetic-native-layout.csv
sha=$(sha256sum "$source" | cut -d' ' -f1)
go run ./cmd/nativeprobe -source "$source" -expected-sha256 "$sha" -out /tmp/fauna-native-layout-unique.json
```

**License/version issue is partly reconciled, not waived.** Original [VHDC site](https://horse.cs.uni-bonn.de/vhdc-home.html) explicitly assigns its source content CC BY-SA **3.0 Unported**. The [Kine2Go dataset LICENSE](https://huggingface.co/datasets/MIMUW-Robotics/kine2go/blame/main/LICENSE) says its **adapted/retargeted horse subset** uses CC BY-SA **4.0**. [Creative Commons' compatibility rules](https://creativecommons.org/compatible-licenses/) permit contributions to adaptations of BY-SA 3.0 work under BY-SA 4.0. Therefore the two statements **need not be contradictory**, provided adaptation provenance, attribution, license stacking and all other obligations are respected. This does **not** mean unchanged source bytes have been relicensed by the original VHDC owner, nor that an original source file or a derivative trained model is automatically approved for unrestricted publication. Keep original 3.0 source and derived 4.0 contribution terms separate in any future rights evidence.

**Outstanding independent W2/W3 gates:** access and hash the exact file from the original VHDC-host URL; compare its bytes with the pinned copied Git blob; verify calibration/time units/axis/reference frame and original 3D capture marker behavior; identify actual horse/day/measurement and derivative ancestry; independently assess dataset/derived-checkpoint rights and physical contact. A compatible CSV header is not native-source authentication. Public experiments remain self-authored and unmerged; $0 synthetic CPU only.
