# Oneirifact public-safe independent DCC R0

This isolated experiment tests **only a synthetic derived geometry artifact** produced by a private Oneirifact R1 implementation. No Oneirifact source code, API credentials, protected character data, identity models, or private configuration is included here. The single input is an indexed GLB of a 2 m cube with a radius-0.4 m cylindrical through-hole, generated with a low-resolution occupancy-grid surface evaluator (detail 16). It is neither exact CAD nor printability-qualified.

- Input fixture: `drilled-box-detail16.glb.b64`; decode with `base64 -d`.
- Exact SHA-256 of decoded GLB: `41f08fdf03eb7458adabd9c0a3026379b01f13bf8db2882cfc2f7a76f732ff35`.
- Independent test: pinned official Blender 4.5.16, import the original GLB, query mesh topology/volume/bounds, export a new GLB, launch **a fresh Blender process** to import again, compare receipts.
- The workflow is a **direct `push`-triggered** public GitHub Actions experiment with standard `ubuntu-24.04`, no Agent Dispatch, paid runners, secrets, or private package access.
- Expected: one connected watertight shell, Euler characteristic 0 (one handle, under closed orientable surface assumptions), finite bounds ±1 m, approximate volume 6.5–7.5 cubic meters and roundtrip consistency.
- Failures: source SHA mismatch, invalid Blender import, non-manifold topology, divergent geometry/bounds/volume or missing files.

This test does **not** verify that Oneirifact source builds on public GHA, nor all mesh features, vertex normals, physically safe printing, or any production release. Project authority and results are reconciled in the private Oneirifact DLE, not in this public experimental branch.
