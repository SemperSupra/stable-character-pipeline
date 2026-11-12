# R014 actual CC0 body material/UV face coverage — verified, not photoreal acceptance
Date: 2026-11-12 | Authority: private R014 #138 and R015 consumer #141 | Disposition: RESEARCH

## Independent actual Blender source evidence

[Public free-tier GHA run 43289453499](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43289453499) — **both original-source CPU material audit jobs PASS**: male saved CC0 morphology candidate from run 43287691272 and female saved CC0 candidate from run 43288582735, each opened in fresh source-verified Blender 4.5.16. The SHA-verified source lookdev pack is `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107`, native pinned MPFB source `6ff1eb358f6c1959ced77e79e6dd2406d9a71f49`. Original source binaries were consumed through short-retention GitHub Actions artifacts and **not committed**.

| Actual saved-source property | Female-associated candidate | Male-associated candidate |
| --- | ---: | ---: |
| Original body vertices | 19,158 | 19,158 |
| Body polygons | 18,486 | 18,486 |
| Weighted deform vertex groups | 291 | 291 |
| UV maps | 1 | 1 |
| Source images packed into native saved scene | 10 | 10 |
| Unpacked external source images | 0 | 0 |
| Body polygons with unassigned material slot | 0 | 0 |
| Main body shader polygons | 17,136 (92.6972%) | 17,136 (92.6972%) |
| Lips shader polygons | 380 (2.0556%) | 380 (2.0556%) |
| Ears shader polygons | 600 (3.2457%) | 600 (3.2457%) |
| Fingernails | 92 (0.4977%) | 92 (0.4977%) |
| Toenails | 200 (1.0819%) | 200 (1.0819%) |
| Nipple-associated material | 78 (0.4219%) | 78 (0.4219%) |
| "genitals" material slot polygon count | **0** | **0** |

The material assignments total 18,486 faces. Most source textures are 2048×2048, others 1024×1024 or 512×512. The seven material slots each have a Blender material output and a **nested shader node group**; direct top-level Principled/image nodes are absent. That does not prove missing PBR; nodes may live inside the group. It also does not prove SSS, packed image linkage to visible surface or correct UVs. A material slot called "genitals" with zero polygons **does not represent verified external reproductive anatomy**.

**Source-native geometry and motion, independently proven elsewhere:** [six adult morphs with rigged GLBs and fresh-process pose proof](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43286258004), [six distinct evaluated mesh hashes instead of identical Basis geometry](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43287728426). [Female CC0 morph/motion run](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43288582735) and [male CC0 morph/motion run](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43287691272) also independently passed. This is not proof that attached eye/hair/teeth geometries remain collision-free under all morphs.

## Development and O&M decisions
- Keep actual source material-per-face assignments as a *diagnostic oracle*, not as photoreal acceptance or rights clearance; require nested shader group graph audit, actual packed texture connectivity, UV bounds and region-quality renders next.
- Separate region-specific skin (SSS), eye cornea/iris/pupil, eyelashes, brows, mouth/teeth/tongue, hair, garments and external anatomy from blanket body-material checks. 4K cinematic renders, temporal consistency, real gait/IK, contact, tissue physics and facial animation remain separate R014/R009 gates.
- Continue source-identical-pinned-mesh DoE for 6 real adult shape-key morphs from [PR #448](https://github.com/SemperSupra/stable-character-pipeline/pull/448). Six is enough for functional coverage smoke, **not** full morphology representation or CPE inverse mapper training.
- No user identity data or private assets were sent to free-tier runners; no third-party model binaries stored in Git. Retain source/blob hashes, short-lived GHA native files, JSON evidence and fail-closed acceptance statuses.
- Source-image references originate from a CC0-labeled upstream asset pack; verify per-asset rights independently before final product release.

## Durable evidence files
- `43289453499-female-material-summary.json`
- `43289453499-male-material-summary.json`

These are exact model-generated stdout JSON summaries from source-native original GHA executions (the full accessory-mesh listing is retained only in original GHA artifacts). **NO MERGE/RELEASE or cinematic photoreal promotion.**


## Bounded nested PBR shader graph follow-up — source verified

**Public free-tier run [43290409906](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43290409906): two independent saved-source Blender 4.5.16 actor jobs PASS.** The source metadata originates from the two material-census fixtures above; no model files were copied into the repository.

Both male/female actors:
- Six **active** body material slots, each with surface-linked Material Output and nested source shader groups containing a **Principled BSDF**, packed source image texture nodes, noise/normal-map/bump adjustments. Two packed image texture node references per active material graph.
- Unused body material slot index 6, named genitals, has **zero assigned body polygons**. The existence of an unused shader graph does not prove geometric anatomy.
- The nested group includes a PBR shader; the source lacks a standalone dedicated BSDF_SUBSURFACE_SCATTERING node, which does *not* rule out Principled BSDF subsurface controls. Those input parameters and actual rendered skin response remain unchecked.
- Nested source inventories are diagnostic graph traversals, not proof all nodes are connected to the final surface, not visual acceptance. Independent shader link reachability, close-up true render review, eyes/cornea, hair collisions, material roughness, SSS, skin displacement, UV seam and asset-body registration are still HOLD.

**Durable compact JSON:**
- `43290409906-female-nested-pbr-summary.json`
- `43290409906-male-nested-pbr-summary.json`

No change to cinema-quality release disposition. No private imagery, no main merge or release.
