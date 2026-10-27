# R4: learned auto-rigging candidate admission — source inspection only

Authority: [public R4 issue #46](https://github.com/SemperSupra/stable-character-pipeline/issues/46), independent of NASA R1/R2/R3/R5 research candidates. Every candidate's evidence URL is upstream-controlled third-party information; do not treat website statements as proof of available rights beyond the exact file/terms and scope. **No learned model was executed.**

This $0 public CPU workcell is a Go 1.23 standard-library-only offline validation of a 5-candidate source and rights ledger. It never downloads weights, datasets, media or character models; it never authenticates, trains, predicts or launches GPU compute. The only GitHub Actions network use is the Actions checkout and official Go toolchain action. It validates that rights are three independent dimensions: source media (person/video/photo), pretrained model/weights, and intended destination rig/character; code license is a fourth separately sourced field. Unknown is not equivalent to granted.

Candidates:
- [UniRig](https://github.com/VAST-AI-Research/UniRig) — input mesh to inferred skeleton/skin, code MIT, source-declared CUDA at least 8 GB, released model-card subset only (https://huggingface.co/VAST-AI/UniRig).
- [SkinTokens](https://github.com/VAST-AI-Research/SkinTokens) — mesh to tokenized skeleton/skin, code MIT, source-declared 14 GB NVIDIA; actual inference not run.
- [MoCapAnything V2](https://github.com/phongdaot/MocapAnything) — video and **separately rigged reference asset** to inferred motion; code/released V2 weights MIT claims but separate Bria RMBG, DINOv2, SAM2 and Truebones rights. Benchmark source/paper split mismatch is not independently tested.
- [SAM 3D Body](https://github.com/facebookresearch/sam-3d-body) — independent still photo to estimated 3D body model, checkpoint is Hugging Face agreement/authentication-gated and SAM License. No open/public weight inference claim or permission assumption.
- [Motion2MixamoRig](https://github.com/MaxLiu22/Motion2MixamoRig) — photo or video to motion on an existing Mixamo rig, code Apache-2.0 while SMPL-X, Adobe Mixamo FBX and ~5GB of various upstream extraction weights each have independent terms, some noncommercial. Do not trigger first-run auto-download.

Source files under `qualification/r4_admission`:
- `candidates.json` contains explicit model/source links, scoped rights and GPU memory from upstream (null means unknown, **not CPU-capable**).
- `main.go` validates allowlisted URLs, no unknown JSON fields or extra appended objects, all four kinds of rights evidence, five stable candidate identifiers and strictly source-inspection status. It outputs `r4-admission-receipt.json` with `model_inferences=0`, `weight_downloads=0`, `GPU_executions=0`.
- `main_test.go` tests negative controls: forbidden downloads/inference/private/paid, wrong source, unknown licenses, mutated rights ledger, forged inference success and duplicate candidates.
- Public standard GitHub Actions Go CI runs all negatives and emits machine-readable receipt in a short-lived artifact. No model/test sample code is imported from upstream.

**Next separate admission** before any actual model test: pin exact upstream commits and model-weight file SHA/license; classify their CPU/GPU envelope, external assets, licensing/territorial/endorsement rights, and an independently rights-admitted public character mesh and media fixture. Request a separate sandboxed free GPU cell only when available, rights and admission validated. The first actual inference will be a new workcell and a new type-tagged receipt, not an upgrade to this source survey.

Humans see this README/rights matrix; automation reads strict input/output JSON and Go exit status; agents see issue #46, exact source SHA/test run, first failures and next admission baton. Preserve all merge/release/deploy, private character, CPE promotion and paid-resource holds.
