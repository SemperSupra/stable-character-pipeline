# R009 — original reusable utility apron, real-source technical derivative

**Date:** 2026-11-07. **Status:** source-verified, locally generated independently skinned garment research; *not* native Blender, dynamic-cloth, human morphology or release acceptance. Public original synthetic source owner: [#292](https://github.com/SemperSupra/stable-character-pipeline/pull/292); existing strict exporter [#303](https://github.com/SemperSupra/stable-character-pipeline/pull/303)/[#338](https://github.com/SemperSupra/stable-character-pipeline/pull/338), scientific 72-frame crossing witness [#340](https://github.com/SemperSupra/stable-character-pipeline/pull/340). Shared public DLE #272; private Naomi research DLE #113 with protected body owner #23.

## Design / objective

Create one **original** reversible generic utility apron, fitted parametrically to both AsterOriginal and JuniperOriginal via the actual self-authored synthetic `wardrobe_v1.glb` producer artifact. Do not copy any copyrighted series art, texture or mesh. This is the reusable clothing architecture's first *new garment* test, not a private human garment.

- Authoring source: public original synthetic #292 exact commit `31d09f2ab079880707a2e2e736af333e5c50e68d`, native run `42074718864`, artifact `13438710020` ZIP SHA256 `90703fcc9554fc70221e5493c4ddadd4e699610aae4ea687b557831fe2dc0b9a`.
- Required `wardrobe_v1.glb` exact SHA256 `470ec8fc159912e8ad2e30733a00c09785e11c1275c26936774690fe2807727b` (2,454,544 bytes), `wardrobe_v1_manifest.json` SHA256 `3b451c215883fbfe70ac0d81370f6be12cdfad7a55622b390bafe3fab2f664ec` (3,470 bytes). Obtain from that exact artifact, **never** from a similarly named source. No original model binaries committed to Git.
- Two separate new `*_Wardrobe_apron` nodes, each with **independent apron-panel and waistband primitives**, 275 vertices / 432 triangles per actor and own skinned `JOINTS_0`/`WEIGHTS_0` on the existing **35-joint** actor skin. Source-bottom mesh measurements determine garment width/depth; locally bounded exact nearest triangle via 48 centroid candidates transfers barycentric skin weights.
- New source-independent `original_apron` preset includes `body,hair,top,bottom,footwear,apron` for both actors. Original `signature`, `alternate`, `unclothed`, meshes, materials, rig, animation and GLB BIN prefix remain unchanged and available.
- Authoring derivative and **separate strict portable derivative** are distinct outputs; inactive clothing nodes have their `mesh` and `skin` properties removed in the derived portable view but the authoring mesh library is retained. Same fix as #303/#338, no overlapping sibling source writes.

## Reproduce (Python 3.11+ with NumPy / SciPy installed)

```sh
cd qualification/original_reusable_characters   # or source script directory
python3 original_apron_garment_v1.py \
  --source /approved-original/wardrobe_v1.glb \
  --manifest /approved-original/wardrobe_v1_manifest.json \
  --master /new-folder/apron_master.glb \
  --portable /new-folder/apron_portable.glb \
  --new-manifest /new-folder/apron_manifest.json \
  --receipt /new-folder/apron_receipt.json
R009_WARDROBE_SOURCE_DIR=/approved-original python3 -m unittest -v test_original_apron_garment_v1
```

Without actual approved source the real-source tests SKIP, not silently pass. All exports refuse to overwrite any existing output path or alias a source path. The local exact source-run completed 15/15 tests; independent trimesh 4.11.1 opened source derivative (23 geometry nodes) and strict portable derivative (18 active geometry nodes) without import errors. This does **not** certify a Blender skin modifier or render.

## First RED and correction (must remain visible)

Original consumer code had a genuine closest-point projection error: interior triangle barycentric weights `(0.5, 0.25, 0.25)` were computed correctly but the returned **point** omitted `w*ac`. The math control failed (`[0.25, 0, 0]` instead of `[0.25,0.25,0]`). This incorrectly inflated nearest-triangle distance evidence. Corrected the projection formula, not the threshold; reran 15 tests PASS, two GLBs regenerated with new hashes. A separate initial test expected a literal docstring phrase absent from the true source; corrected that assertion. Local initial `local_unittest.log` retained; tests now reproduce the fixed math.

## Current local evidence / unaccepted steps

| Item | Result |
| --- | --- |
| Exact input artifact/master SHA, source class and manifest | PASS |
| Original body/skin/animation and BIN prefix unchanged | PASS |
| Two independent 35-joint skinned garment meshes | PASS structural |
| Apron panel per actor | 225 vertices / 384 triangles |
| Waistband per actor | 50 vertices / 48 triangles |
| All new weight sums 1.0 and joint index 0..34 | PASS |
| Barycentric local rest reference distance p95 | ~50–52mm, outside body as intended; NOT signed collision proof |
| Source-free math controls + exact-source integration tests | 15 PASS locally after first RED correction |
| Blender native import, all72 deformation/skin/render | **NOT RUN** |
| Full triangle BVH collision, volumetric containment, self-intersection, cloth physics | **NOT RUN / UNKNOWN** |
| Facial/shoulder/human morphology, actor likeness | **NOT ACCEPTED** |
| Protected Naomi/Alison, private source permissions, public release/CPE | **NOT TESTED / HELD** |

### Next workcell

Independent original-only Blender 4.5+ importer should verify both new garment nodes with armature modifiers/skin, exactly 35 joints each; native frame 1–72 deformed mesh edge strain and body/clothing crossings via existing #340 witness; explicit winding-aware volume containment and three-camera temporal samples; CPE and rights remain separate gates. If native fail, retain first RED and do not claim garment portability. This workcell intentionally adds **no** public Actions workflow to avoid unnecessary fanout; execute in an approved existing public free-tier native test path after source-owner dependency review.

**Hygiene:** new child draft branch based on exact #292 head only; no authoring base/edit, no private model or GHA, no main promotion, rebase, deletion, merge or release. Heavy generated original-synthetic GLBs and preview evidence stay out of Git; owner-private Drive only if bytes are subsequently uploaded and independently rehydrated with matching SHA.
