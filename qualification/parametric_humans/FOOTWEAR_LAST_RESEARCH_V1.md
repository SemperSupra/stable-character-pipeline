# R009 — source-bound footwear last and ankle-opening research v1

**Status:** Research-only, not accepted as physically correct shoes, comfortable wearable footwear, realistic male/female character anatomy, natural gait, full triangle collision-free motion or a release asset. No protected Naomi or Alison inputs.

## Authority and source

- Existing original-only R009 public draft child PR #336 and public DLE issue #272. Do not merge/rebase, close, delete, release or CPE-promote; parent #308 exact base SHA drift remains held. Master→Aster mapping still provisional; alternate male garment owner #337 is separate.
- Fitted **source**: original Aster/Juniper + MakeHuman CC0 candidate, previously fitted top/bottom/trim, exact GLB SHA256 `366fc2964e0e156988b0207735d89b8dbba18d6b92d0ac453e0d4fc7846fe99f`.
- Fitted **derived GLB**: SHA256 `a8b493eaba59c965713f4f70f0dccebebcfcc4f3d4ba9aa712d79915e1a05739`, retained original body/rig/animation and inactive source shoe mesh library. Open ankle edge is intentional.
- Generator `footwear_last_v1.py` reads only pinned original-source GLB. It does not import proprietary assets or fetch the internet; dependencies are Python, NumPy, SciPy and VTK plus existing project-original scripts.

## First failures, rejected alternatives, corrective work

1. Existing footwear has ~19.68% signed vertices embedded more than 5 mm in the retargeted body at REST. Naively projecting the *old* shoe mesh reduced inclusion but reversed 1.1–1.7% triangles and stretched edges >6×: **rejected**.
2. A conformal offset of a clipped body foot shell reversed ~10% of face normals: **rejected**; no weakened quality gate.
3. New foot-section rings based on a support function wrongly treated as radial distance were oversized at diagonals; replaced with the actual radial distance computed from the planar convex hull's half-space inequalities.
4. A fully capped anatomical last still intersected the ankle (~1.34% to 1.47% sampled vertices) and looked like a closed sock; corrected by clipping an actual top opening at Y=0.14 m. No surface bridge is added across the ankle.

## Actual measurements

- 2 actors × 2 shoe components, each with 35-joint skin and unchanged one source animation.
- New shoe mesh per actor: **1,665 vertices, 3,250 triangles**; two connected components (left/right), consistent face winding, zero sampled zero-area triangles, open boundary by design, no watertight-shoe claim.
- Rest signed footwear-vertex inclusion (more than 5 mm inside body): **0/1665 = 0%** for each actor.
- Full **72/72 source-original CPU animated frames per actor**: maximum signed footwear inclusion = **0%** for each actor, with positive/negative sign calibration performed in the shared observer. The 72-frame contact is **vertex inclusion only**, not triangle–triangle collision, subsurface collision, friction or native Blender.
- Other garments from the exact same candidate: top and trim 0% across these sampled 72 frames; skirt worst Aster **2.5%** (frame 16), Juniper **1.875%** (frame 12). Those are still failures to correct.
- Shoe soles extend about 10 mm below the previously calibrated foot base. Thus foot-on-floor/contact and realistic sole shape are **NOT accepted**. Shoe opening/wearability, thickness, leather/fabric material, toe articulation, leg-to-boot seal, selected gender-specific wardrobe and stylization remain held.

## Execute and validate

With source and exact project scripts adjacent on PYTHONPATH:

```bash
python3 -m unittest -v test_footwear_last_v1 test_footwear_last_contract_v1
python3 footwear_last_v1.py --input source.glb --output candidate-shoes.glb --receipt candidate-shoes.json
python3 observe_footwear_last_72_v1.py --input candidate-shoes.glb --sha256 a8b493eaba59c965713f4f70f0dccebebcfcc4f3d4ba9aa712d79915e1a05739 --out shoe-72-vertex.json
```

`R009_SHOE_SOURCE=/path/to/sha-pinned-source.glb` enables the real-original-code test; otherwise the exact-byte test is explicitly skipped. **8/8 local tests passed**, including actual-source provenance/rig/triangles/weight normalization and deterministic two-build bytes. The standard public CI executes source-only tests without private model bytes. The true source-bound tests and VTK render are performed locally and archived with their evidence, not misrepresented as public Actions test coverage.

## Durable placement and next baton

- Git/DLE: source scripts, hostile tests, compact verified evidence JSON and executable batons on the existing R009 #336 workcell and #272 DLE. Do not add a parallel branch/issue/job or copy protected real-person models to public Git.
- Owner-private Google Drive: original+derived glTF binaries, source-hash manifests, static VTK front/side/shoe preview, full motion summary, first failures; post-upload raw-byte/ZIP CRC readback mandatory.
- Next independent work: native Blender 72-frame evaluated geometry + 2-camera foot/ground interaction; check triangle–triangle shoe/body intersection, footwear sole/floor contact, skirt collision at worst frames; retarget official gender/phenotype macro targets under separate #337 ownership and human visual review.
