# R037 — original synthetic render comparison (first executable workcell)

Authority: private Stable Character DLE issue #176. Existing preference authority #145; critic #168; source P0 #167; material predecessor public draft PR #491 and Gaussian-splat predecessor public draft PR #507.

**What this is:** a real, source-safe, free public CPU Blender Cycles two-arm rendering and structural comparison experiment. The stylized abstract bust is generated from Python code. No external models, protected data, private people, pretrained weights, copyrighted media, secrets or GPU expenditure.

**What this is not:** evidence that anyone can generate a photoreal human, that skin is optically correct, that an image model outperforms a baseline, or that an actual human preference has been learned. All outputs remain research-only.

## Executable work

The same original synthetic bust, geometry, static pose, camera, seeds and samples are rendered twice through Cycles. Arm A is baseline Principled shading; Arm B changes only materials: conservative SSS, roughness and procedural microbump. The test emits real beauty PNGs, genuine Blender multilayer EXR render passes, and SHA-256 receipts for source ID, actual mesh vertices/faces, camera, animation and artifacts.

A separate Go stdlib validator independently checks:
- Strict JSON (rejects duplicate keys, unknown keys and trailing content), version, seed, status, rights and valid finite positive render time.
- Actual SHA-256 for both PNG and EXR, image decode and nonblank pixel diversity, EXR magic header and bounded file size.
- Exact source ID, mesh geometry, camera, animation, seed, image resolution and samples shared by both arms.
- Evidence that the two render colors actually differ. This only proves a visible material change, *not* improved realism.
- Negative controls for source/rights mismatch, camera/pose drift, geometry mutation, digest tampering, path traversal, blank images, bad JSON and invalid numeric values.

## Run locally

Install Go 1.23+ and Blender with Cycles.

    cd renderlab
    go vet ./...
    go test -race ./...
    cd ..
    mkdir -p out/baseline out/physical_material
    blender -b -t 2 --python renderlab/synthetic_scene.py -- --arm both --output out
    (cd renderlab && go run . -baseline ../out/baseline/receipt.json -material ../out/physical_material/receipt.json -out ../out/comparison.json)

Public GHA workflow: .github/workflows/r037-synthetic-render.yml. It uses only standard public Ubuntu runners, read-only checkout, pinned Actions, bounded timeout and 3-day artifacts. Missing Blender package or runtime failure is FAIL, never disguised as PASS. Git DLE receipts must cite exact commit, workflow run, step and output SHA.

## Interpretation

PASS_RENDER_ONLY means Blender returned PNG+EXR files and receipt; not an external visual review.

PASS_STRUCTURAL_RENDER_DIFFERENCE_ONLY means Go verified paired source/geometry/camera/animation/seed, real PNGs, nonblank images, file SHA and pixel differences.

NOT_PHOTOREALISM_OR_HUMAN_PREFERENCE_EVIDENCE is deliberately embedded in all comparison receipts.

Current Go EXR test checks valid magic + SHA and size but does NOT decode EXR pass channels. That stronger, independent check is a next gate.

## Follow-on work

- Reuse proven real human PBR baseline from public #491 after admission, not duplicate a new renderer.
- Consume R033 independent visual critics and R016 source-authenticated human preference events; no duplicate preference authority.
- Introduce admitted mesh-embedded Gaussian, constrained diffusion and temporal video arms; use frozen paired settings and blinded human comparisons.
- Make real depth/normal/segmentation and temporal outputs independently testable, with anatomical and identity gates before model scoring.
- Crossfeed every PASS_NARROW / FAIL / HOLD / QUOTA_BLOCKED and exact source SHA into private DLE #176. Keep public original synthetic artifacts separate from protected character data.

Initial actual public free-CPU structural PASS: https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43806174419 at exact source SHA 676d332b6da3005cd874a1ada47706f2b4ec97b6. Real artifacts contain beauty PNG, multilayer EXR, receipts and an independent Go comparison; the result is not human photorealism acceptance.
