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
The original v1 `wardrobe_export_preset.export` still owns the source/preset semantics but is **not** sufficient for an independently portable GLB: it detaches inactive garment nodes from the scene root while retaining orphaned `mesh` bindings. Official native Blender imports the mesh-bearing orphans anyway, causing strict A5 **FAIL** on [first run 42116286310](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/42116286310).

The new **opt-in** `wardrobe_portable_export_v2.py` wraps v1 in an ephemeral directory and strips the inactive orphan nodes' `mesh` and `skin` *bindings in the derived portable GLB only*. It retains the original mesh definitions, full authored skin joint arrays, animation, and unchanged source bytes. `wardrobe_console_v2.py export` now invokes v2. `wardrobe_portable_blender_v2.py` remains **strict and unchanged**, importing real derived GLBs and comparing exact layer sets and 35-joint armature modifiers.

[Exact-source CI run 42140530484](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/42140530484) **PASS**: 11/11 adversarial source tests, 72-frame native deformation, and independent Blender import of unclothed, signature and alternate presets. Inactive garment objects are no longer imported. This resolves only the **A5 portability defect**, not garment-body collision or aesthetic acceptance.

Source artifact `13467652329` ZIP SHA-256 `bd52435b74660e1b38d17d265e8282d08ae5789ef02ebd2e6b70b9d6a4b6052b`, 1,918,114 bytes, all 14 internal file hashes verified. Long-term owner-private Google Drive custody and full-byte download-back **PASS**: [R009 Wardrobe QA archive](https://drive.google.com/file/d/1iWWX7jD9nJO-A5nacTVHp6UKwOMBHvBy/view?usp=drivesdk) in [R009 Wardrobe Strict GLB QA folder](https://drive.google.com/drive/folders/1rbc36JQuajE21I7Fd_4NLvl6s53lEwv9). Original native first failure remains recorded and held as a regression witness.

This is structural/viewer interchange and non-destructive source custody, **not** physics, full-body anatomical correctness, cloth fit, or realistic character qualification.

## Public $0 independent runner
The isolated root `.github/workflows/r009-original-wardrobe-refinement-v2.yml` executes source tests, deterministic outputs, SHA-verified official Blender CPU, all72 weighted deformation witness, and native import of unclothed/signature/alternate portable GLBs on a standard **public** GitHub Actions runner. Evidence is produced on a short-retention public Actions runner, now with a source-scope parent-SHA hygiene gate and self-verifying ZIP-root SHA256SUMS. The first successful strict A5 artifact was already copied to owner-private Drive and independently verified byte-for-byte; new artifacts require the same verification before any long-term custody claim. Record exact CI SHA, native first failures, digest and scope in DLE.

## Fail-closed holds
- Parent #291/#292, original #271/#289/#290, MIT #287, protected Naomi/Alison, and G5/G9 private #103 are untouched.
- Preserve original cropped 16:9 preview, chest bleeding, hip seam and strain defects as first failures.
- A successful structural run is not full anatomical continuity, no garment-body intersection, no normalized JCS/ROM, natural gait, or owner visual acceptance.
- No external asset or private identity, no private GHA minutes, no owner-source merge, branch cleanup, license grant, release, deployment or CPE promotion.
- Git/DLE owns code/decisions/receipts; large media belongs in owner-private Drive with measured SHA and custody proof.
