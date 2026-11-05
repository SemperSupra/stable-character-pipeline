# R009 — Parametric Synthetic Human Contract v1

Status: **source/schema prototype only; anatomical, fitting, visual, clinical, and release qualification UNKNOWN**.

This independent additive workcell is based on the OPEN/DRAFT original-human modular wardrobe PR #292 at exact commit \`31d09f2ab079880707a2e2e736af333e5c50e68d\`. The competing wardrobe refinement #303 is a **sibling**, not a source dependency. It currently has an independently established Blender portable A5 FAIL; do not adopt its portable GLB exporter as accepted.

## DOPAV / scope
- **Discover**: Parent 35-joint original human source and shared agent reconstruction supervisor PR #300/#301; **do not duplicate agent control plane**.
- **Observe**: Fixed 35-joint art-style anatomy is not a statistically validated body model. No underlying scanned, identifiable, or licensed third-party body data is in this workcell.
- **Plan**: Parametric schema/state, synthetic deterministic generator, temporal surgical/styling event contract, negative tests and backend/source catalogs.
- **Apply**: Stdlib \`parameters_v1.py\` and \`test_parameters_v1.py\`, independent from mesh generation.
- **Verify**: Run \`python3 -m unittest -v test_parameters_v1\`; CI will record evidence and SHA. Passing proves data-contract consistency **only**; no claim of biomechanical realism or picture/video fitting.

## Reproduction (no installs, $0 local or public Linux Actions)
\`\`\`sh
cd qualification/parametric_humans
python3 -m unittest -v test_parameters_v1
python3 parameters_v1.py catalog
python3 parameters_v1.py generate --seed 73 --out synthetic_73.json
python3 parameters_v1.py validate synthetic_73.json
python3 parameters_v1.py snapshot synthetic_73.json --date 2026-11-05
\`\`\`

Generation refuses overwriting existing output. Runs are deterministic for a fixed Python implementation and seed; record interpreter version, Git SHA, schema and resulting canonical SHA. No medical procedure prediction, no assertion of surgery from observed image changes, and no real-person identification.

## Contract and invariants
1. \`character_id\` and immutable \`identity\` coefficients remain stable across time-indexed states.
2. Semantic controls have explicit paths, units and rough engineering safety guards; they are **not clinical population reference ranges**.
3. Changes to physique or appearance are dated **non-destructive delta records**; surgical terminology is a representation category, not verification of an actual procedure.
4. Every event carries evidence classification. Image-fitting actors must explicitly mark occluded/uncertain parameters \`unknown\` and never infer exact concealed anatomy.
5. Parameter sampling contains simple correlations but **is not population calibrated**, and must not assign anatomy by nationality or ethnicity.
6. The same contract will be exposed to humans, CLI/API clients and automated actors. It does **not** implement or replicate the existing shared supervisor.
7. A mesh adapter must validate unit, axis, neutral pose, correspondence, skin weights, deformation, collisions, portable GLB and inverse fitting on separate test fixtures.
8. Proprietary and third-party source, licenses, real people, and protected private R009 Naomi/Alison are **out of scope**.
9. Source and DLE in Git; large media/meshes in governed owner-private Drive with full-byte SHA verification.
10. Public Actions only; no merge, release, deployment or CPE without owner gates.

## Next independent workcells (not yet implemented)
- **P1b** Adapter map from semantic controls to original 35-joint geometry and rig, with counterfactual previews and unchanged source bytes.
- **P2** Exact upstream backend audit, per artifact/operation rights, offline performance, 3D geometry/fitting benchmark (MHR, SOMA-X, Anny, isolated MPFB, FLAME).
- **P3** Human anthropometry measurement definitions, valid joint distributions and applicability/coverage audits; catalog links are **research leads, not authorized datasets**.
- **P4** True hair geometry, iris shaders, skin reflectance, regional sculpt, garment-aware fit and all72 motion deformation.
- **P5** Temporal morphology state and procedure representation fit against synthetic ground truth and calibrated follow-up observations; not predictive medicine.
- **P6** Still/video adapter to existing shared supervisor with independent evidence and held-out views.

**First RED / active holds:** Sibling #303 A5 portable importer fails due stray garment nodes; regression retained in #272. Existing R009 anatomical quality, actual cloth-body penetration and identity evidence remain FAIL/UNKNOWN as appropriate. Keep private protected sources separate.
