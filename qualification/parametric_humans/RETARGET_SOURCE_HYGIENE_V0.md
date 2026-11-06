# Retarget v0 exact-source DOPAV correction (2026-11-07)

- Scope: public original Aster/Juniper + source-pinned official CC0 MakeHuman body only. No Naomi/Alison inputs.
- First local RED: `ImportError: cannot import name CANDIDATE_GLB_SHA256` while loading the independent motion and garment validators.
- Root cause: source producer pinned its two input hashes but omitted the first generated candidate GLB hash imported by the downstream validators.
- Correction: add `CANDIDATE_GLB_SHA256` to `retarget_makehuman_v0.py` with byte-verified existing GLB hash `57a4cfd1d9df7e6e2f7c2e44e68765a8ca4357895d5b075f9229b78a5bbcd36a`; no source-bypass, tolerance relaxation, or source asset mutation.
- Local actual-input tests: `PYTHONPATH=... python -m unittest -v test_retarget_makehuman_v0 test_observe_makehuman35_motion_v0 test_fit_signed_clearance_v0 test_weight_transfer_regularize_v1` **27/27 PASS** (2026-11-07). These require NumPy, SciPy, VTK, and exactly pinned private-custodied source-original GLBs; public GHA must not acquire protected source.
- Scientific holds: source→target rest pose and 35-joint weight transfer approximate, no anatomical or identity acceptance; observed top/skirt/trim rest collision repair is insufficient for 72-frame cloth; footwear still penetrates, Aster masculine morphology is provisional, face orientation changes, eye/face artifacts; static VTK is not native Blender.
- CI policy: new Python files are independently compileable on standard public Actions; running actual-source tests on public runners requires a separately approved *public-safe source-original* fixture, so no false CI pass based on skipped exact-source cases.
- Merge, branch cleanup, CPE/release, rights changes and parent SHA drift remain HELD; owner DLE #272.
