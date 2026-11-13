# R014 — Actual source CC0 appearance attachment defect and first native corrective
Date: 2026-11-13 | R014 authoritative private issue #138 | R015 semantic consumer #141 | All promotion/merge/release HOLD

## Real observed defect: body's shape keys changed; accompanying accessory meshes did not

- Independent public GHA [43364343468](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43364343468), [negative-control draft #471](https://github.com/SemperSupra/stable-character-pipeline/pull/471), exactly SHA-gated official source CC0 MPFB+MAKESKIN original Blender scene (source public [run 43207664661](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43207664661)) and morphed female/male source qualification ([43288582735](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43288582735), [43287691272](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43287691272)).
- Each actor had six common actual Blender accessory meshes: `eyebrow001`, `eyelashes01`, `high-poly`, hair `long01` or `short01`, `teeth_base`, `tongue01`. All twelve accessory SHA256 hashes from 512 deterministically sampled actual **world-space** mesh vertex positions rounded to 7 decimals were **unchanged** in the morphed source, despite parent body-shape motion.
- Per-actor maximum changed **mean nearest-body polygon distance**, in *uncalibrated native Blender units*, was female **0.037422** (tongue) and male **0.1083388** (short hair). This demonstrates **missing shape propagation to the accompanying assets** in this source pipeline. This is NOT a watertight intersect/penetration classification or proof that a named surface visibly fails; body-shell normals and UV/hair direction may still require independent review.
- Public source geometry and existing rig are retained; no original/source file overwritten. Original both-sex evidence ZIPs CRC-checked, three JSONs each. Private Drive custody [female](https://drive.google.com/file/d/1KYIkkntjI3vEVLc9Bf_USkhkHbNLDV04/view) and [male](https://drive.google.com/file/d/1ob-2yNxVNxv6JMryKntaSAW9lygHfDWV/view), readback confirmed unshared.

## Experimental source-native corrective

- New stacked [draft PR #472](https://github.com/SemperSupra/stable-character-pipeline/pull/472), [original exact-head public GHA #43365071496](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43365071496), two independent disposable CPU Blender 4.5.16 workflows, both **SUCCESS / PASS_EXPERIMENTAL_NATIVE_MESH_TRANSFER_AND_REVIEW_FILES_ONLY**.
- The source-mesh-barycentric method reads original evaluated MPFB triangle vertices and *verifies equal source/morphed evaluated triangle topology/index correspondence*. For each original accessory vertex, find the nearest source body triangle, map the nearest surface point through barycentric correspondence to the **new native morphed body triangle** and apply the 3D body-surface displacement in the accessory's local coordinate frame; update any associated shape-key blocks. The existing rig and original actor body are not modified.
- Both actors: six of six accompanying accessory meshes actually moved, six of six had **smaller discrepancy between source-body mean distance and new-body mean distance** (only a nearest-surface proxy). Native Blender source saved and independent fresh Blender process reopens/can re-evaluate all six corrected assets; two original Cycles technical renders per actor at rest and frame 8.
- Detailed individual distances, in *uncalibrated Blender units*:

| Actor / asset | Original source mean gap | Morphed uncorrected mean gap | Corrected mean gap | Max accessory vertex movement |
|---|---:|---:|---:|---:|
| Female brows | .0007131 | .0270217 | .0007130 | .3731667 |
| Female eyelashes | .0014161 | .0279311 | .0014153 | .3722490 |
| Female high-poly | .0012107 | .0335226 | .0012068 | .3730017 |
| Female hair | .0232207 | .0342285 | .0228509 | .3873467 |
| Female teeth | .0100498 | .0454011 | .0099924 | .3661601 |
| Female tongue | .0148931 | .0523119 | .0148914 | .3661336 |
| Male brows | .0007790 | .0632645 | .0007790 | .1286971 |
| Male eyelashes | .0015045 | .0534233 | .0015037 | .1282223 |
| Male high-poly | .0012767 | .0508739 | .0012733 | .1285900 |
| Male hair | .0108086 | .1190931 | .0105889 | .1326564 |
| Male teeth | .0110198 | .0099257 | .0109384 | .1268726 |
| Male tongue | .0160803 | .0165706 | .0160324 | .1268467 |

- Two corrected ZIP archives independently inspected: Python zipfile `testzip()` **CRC CLEAN**, all source PNGs and corrected .blend matched **embedded per-file SHA256**. Female corrected native .blend **38,301,158 bytes**, SHA256 `f075f6578e3f6e2911a85f64d37b21d080f9afd35dcd79ea064b2216ae73a56f`; corrective ZIP SHA256 `fd9e747f2ef8e6f5ef44360763fa82cbfae4ca4315023b1c7b6ddfe3de944aac`. Male corrected native .blend **35,999,878 bytes**, SHA256 `4fffe83b03865f5735480f66328d6e695577da7c0f4f09fef690c75e1edccb8a`; corrective ZIP SHA256 `dcdeafe45192e58189cbec283a587ca34b368b7d884e7a1daa8508eca16c0ccf`. These are reproducible synthetic assets; no upstream source archive redistributed in Git.
- Persistent private research custody, verified metadata/size in existing [R014 RigLab](https://drive.google.com/drive/folders/19bzvrQ35DwIxdpftrDCjxezNLa2UQl-v): [female corrected .blend and Cycles PNGs](https://drive.google.com/file/d/1VSeDYxQhyP-L-h6mGtP_GcQI4-OP72d3/view) and [male corrected .blend and PNGs](https://drive.google.com/file/d/18npholrwt-ZlUdrZp-R3TfgyRLrZ_OiU/view).

## Real visual QA observations / independent acceptance hold

Manually inspected both actual 448×576 rest and posed Cycles renders. Full adult synthetic silhouettes, hair and facial objects remain recognizable; surfaces look smooth/flat, facial expression is neutral, few visible realistic skin details, and pose is limited/artificial. Render quality is far short of cinematic skin/hair/eye realism. This is **not** an accepted anatomical variation, facial interaction, static/animated contact, or 4K cinematic proof. Body, rig and materials after corrective require independent quality/skin deformation testing through the full motion envelope.

**P0 next:** (1) independent watertight-appropriate contact, triangle intersection, eye/cornea/lash/hair scalp/teeth collision region oracles (positive and negative controls), (2) transfer validation for ALL extremes across the 40 true unseen shapes, (3) pose- and shape-key combination with 16+ keyframes, skin volume, UV and attachment preservation, (4) face/lip/teeth and hair/cloth dynamics; only then high resolution PBR cinematography and user-prompt/CPE model integration.

Owner boundaries unchanged: real MPFB/MHR anatomy R014 #138, native semantic/canonical user descriptions R015 #141, final film/video acceptance R009 #23. Preserve CPE's lossless concept semantics independently of action eligibility. No private data, no paid private GitHub Actions runs, no installation on persistent hosts. Source PRs #471/#472 remain DRAFT/UNMERGED; public main untouched.
