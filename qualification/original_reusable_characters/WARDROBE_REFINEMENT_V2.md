# R009 original-only adult wardrobe v2 — bounded corrective workcells

Source authority: public DLE #272. This is an **opt-in derived candidate**, not a replacement of #291 or #292. Parent #292 source HEAD at branching: `31d09f2ab079880707a2e2e736af333e5c50e68d`. #291 HEAD: `ce0a2743ec5d8c10fd683245cc898d33bb759025`. All original source and protected people remain distinct.

## A1 — body topology
`wardrobe_refinement_v2.py` replaces separate torso and neck/head loft rings with **one weighted and continuously indexed torso→neck→cranium surface** (36 circumferential segments, smooth transitions). The face features, arm/leg tubes, hands, feet and pelvis attachments are still separate intersecting surfaces. **Do not call the entire adult body watertight, anatomically correct or sculpt accepted.** No original source branch was edited.

## A2 — jacket/trouser skin and deformation
`wardrobe_deformation_blender_v2.py` uses the actual imported native Blender armature, asserts one 35-bone armature modifier per body/garment object, inspects nonnegative normalized vertex groups, and evaluates the signature and alternate top/bottom across **all 72 animated frames**. It records source SHA, sampled edges, absolute relative p99/max edge strain, actor and slot. A >25% p99 proxy is flagged FAIL; below threshold stays UNKNOWN. It **does not** claim cloth-body collision detection, joint-axis validity, realism or human acceptance.

## A3 — genuinely different cuts
Within unchanged slots `alt_top` and `alt_bottom`, newly generated independent ring meshes replace the prior cloned same-cut colorways: **cropped sleeveless vest** and **flared calf-length culottes**. They inherit each actor's 35-joint skin index with normalized joint influences. The `signature` garment meshes, `body`, `hair`, `footwear`, actor roots, 72-frame animation, and parent sources remain available. This is authored procedural garment construction; there is no third-party source.

## A4 — three-audience UX/DX
`wardrobe_console_v2.py` provides deterministic human-readable or JSON `inspect`, hash-bound `export`, and executable-argv `plan-blender` modes. It reuses the v1 preset and slot contract. A single source manifests actor selection; source/receipt paths cannot alias. No interactive UI acceptance is claimed; the Blender Outliner remains the graphical affordance.

From `qualification/original_reusable_characters`:

```sh
python3 -m unittest -v test_wardrobe_refinement_v2 test_wardrobe_console_v2
python3 wardrobe_refinement_v2.py --out /tmp/r009-refined.glb --manifest /tmp/r009-refined.json --receipt /tmp/r009-refined-build.json
python3 wardrobe_console_v2.py inspect --input /tmp/r009-refined.glb --manifest /tmp/r009-refined.json --human
python3 wardrobe_console_v2.py export --input /tmp/r009-refined.glb --manifest /tmp/r009-refined.json --out /tmp/r009-alternate.glb --receipt /tmp/r009-alternate.json --aster signature --juniper alternate
```

For Blender saved scenes, use `wardrobe_console_v2.py plan-blender --source scene.blend --out variant.blend --receipt variant.json --preset alternate --actor AsterOriginal` and execute the JSON `argv`. The derived `.blend` must not overwrite the original.

## A5 — portable GLB qualification
The v1 `wardrobe_export_preset.export` remains the only export engine. Its source-anchored three-viewer presets and per-actor combinations are independently checked at the exact GLB scene-root and skin-index levels. `wardrobe_portable_blender_v2.py` then imports **actual portable GLBs** using native Blender and verifies that only expected garment objects appear with functional shared 35-bone rigs. All geometry/skin/animation data is retained inside the GLB; inactive scene-graph nodes are detached, not deleted. This is structural/viewer interchange, not physics/realism.

## Public $0 independent runner
The isolated root `.github/workflows/r009-original-wardrobe-refinement-v2.yml` executes source tests, deterministic outputs, SHA-verified official Blender CPU, all72 weighted deformation witness, and native import of unclothed/signature/alternate portable GLBs on a standard **public** GitHub Actions runner. Evidence is a short-retention technical Actions artifact; promote original large binaries to private Drive only after verified whole-byte custody. Record exact CI SHA, native first failures, digest and scope in DLE.

## Fail-closed holds
- Parent #291/#292, original #271/#289/#290, MIT #287, protected Naomi/Alison, and G5/G9 private #103 are untouched.
- Preserve original cropped 16:9 preview, chest bleeding, hip seam and strain defects as first failures.
- A successful structural run is not full anatomical continuity, no garment-body intersection, no normalized JCS/ROM, natural gait, or owner visual acceptance.
- No external asset or private identity, no private GHA minutes, no owner-source merge, branch cleanup, license grant, release, deployment or CPE promotion.
- Git/DLE owns code/decisions/receipts; large media belongs in owner-private Drive with measured SHA and custody proof.
