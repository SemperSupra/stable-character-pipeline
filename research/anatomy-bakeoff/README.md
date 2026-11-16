# Anatomy bake-off — public synthetic contract smoke (Wave 0)

This standalone, **original synthetic** Go standard-library fixture exercises a narrow anatomical-viewer interoperability contract. It does **not** download or contain real anatomy, private characters, donor meshes, weights, or a physics engine. It makes no medical or model-quality claims.

## Reproduce ($0 CPU, no network/credentials)

```sh
cd research/anatomy-bakeoff
GOTOOLCHAIN=local GOPROXY=off go test -count=1 ./...
GOTOOLCHAIN=local GOPROXY=off go vet ./...
GOTOOLCHAIN=local GOPROXY=off go run ./cmd/anatomyprobe describe
GOTOOLCHAIN=local GOPROXY=off go run ./cmd/anatomyprobe inspect
GOTOOLCHAIN=local GOPROXY=off go run ./cmd/anatomyprobe toggle --system circulatory --visible=false
```

The `describe` result is machine-readable capability discovery for automation/agents. `inspect` emits a semantic scene and original synthetic view state. `toggle` emits a deterministic view-only receipt, with physics digest unchanged. Failures exit nonzero and emit structured error messages. The same contract can be projected into an accessible web tree and supported tooling, but **none is implemented by this probe**.

The hard invariant is orthogonality among present anatomy, rendering visibility, collision and physical simulation. A hidden mesh may still exert forces. Here we independently hash a synthetic physics state; this is NOT an execution of biomechanics. The hierarchy, labels and forces are invented test values, not anatomical ground truth.

## Next independent bake-off lanes

A. Rights/versions/licensing/source classification: BodyParts3D, Z-Anatomy, HuBMAP, Visible Human, Open Anatomy.
B. Fit/prior: MHR, SKEL/OSSO and permitted segmentation tools.
C. Rigid and muscular dynamics: OpenSim, MyoSim/MyoSuite/MuJoCo, ArtiSynth.
D. Tissue/FEM: SOFA, ArtiSynth, FEBio, specialized organ/vascular donors.
E. Human keyboard/screen-reader WCAG 2.2 AA-oriented tree, automation CLI/API, agent semantic tools, build/deploy/upgrade/rollback operations.
F. Compose and qualify paired candidates with small source-clean reference fixtures, measured CPU/runtime/precision/first failure; only then scale.

Per-donor: pin revision, code/data/weight rights separately, define input+oracle+negative mutant+resource budget, output actual command/run environment, SHA and PASS_NARROW / FAIL / UNKNOWN / NOT_RUN. No private Actions spend, publication of third-party or protected data, merge, release, or deployment.
