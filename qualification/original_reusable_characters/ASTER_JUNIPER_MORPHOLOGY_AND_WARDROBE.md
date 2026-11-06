# R009 Aster (Master) / Juniper appearance and wardrobe — research workcell

## Source of authority and identity mapping

Owner direction 2026-11-06: **Master is male and must look masculine and wear masculine clothing; Juniper is female and should look more feminine.** Current original public dataset keys are `AsterOriginal` and `JuniperOriginal`. Interpret "Master" provisionally as the existing Aster character (possible speech-to-text alias), **without renaming or merging character identities**. Resolve the alias in the protected character registry before final promotion.

Owning technical authorities: public [R009 DLE #272](https://github.com/SemperSupra/stable-character-pipeline/issues/272); removable source-original wardrobe parent draft [PR #292](https://github.com/SemperSupra/stable-character-pipeline/pull/292), exact source `31d09f2ab079880707a2e2e736af333e5c50e68d`. Protected identity/source and third-party asset admission remain separate. No rights, release, CPE, or merge promotion.

## Delivered research primitive (NOT visual approval)

`parametric_morphology_v1.py` creates a non-destructive GLB + matching derived wardrobe manifest, leaving the original combined GLB and its manifest untouched. Input and output hashes are recorded. Both bodies, groom, and existing separate garments remain skinned to their existing 35-joint rigs; animation channels and skin structures are unchanged. Local vertex normals and position-accessor bounds are updated consistently. Existing portable wardrobe exports can render the resulting geometry with independent actor outfit choices.

Parameters are independent continuous controls in metres/ratios, **not assumptions inferred from anatomy or sex**:

| Parameter | Aster / male default | Juniper / female default | Intended surface |
|---|---:|---:|---|
| Shoulder width | 1.090 | 0.965 | torso/upper garment |
| Chest depth | 1.065 | 1.020 | upper torso/garment |
| Waist width | 0.980 | 0.930 | waist/garment |
| Hip width | 0.965 | 1.075 | lower torso/trousers |
| Jaw width | 1.090 | 0.955 | face |
| Brow projection (m) | 0.007 | 0.002 | face |
| Chin projection (m) | 0.006 | 0.002 | face |
| Bust projection (m) | 0.000 | 0.017 | optional front chest/garment |

Sex labels are owner-set metadata. Every scalar can be independently tuned or applied to either actor (e.g., narrow-shouldered male, broad-shouldered female). Do not infer identity, age, or sex from measurements. Profiles are validation-bounded; no explicit anatomical genital geometry is generated.

### Run and interchange

```sh
cd qualification/original_reusable_characters
python3 -m unittest -v test_parametric_morphology_v1

python3 modular_wardrobe_v1.py --out /tmp/r009-wardrobe.glb --manifest /tmp/r009-wardrobe.json
python3 parametric_morphology_v1.py \
  --input /tmp/r009-wardrobe.glb --manifest /tmp/r009-wardrobe.json \
  --out /tmp/r009-morph.glb --out-manifest /tmp/r009-morph.json \
  --receipt /tmp/r009-morph-receipt.json
python3 wardrobe_export_preset.py \
  --input /tmp/r009-morph.glb --manifest /tmp/r009-morph.json \
  --out /tmp/r009-audience-preview.glb --receipt /tmp/r009-preview.json \
  --aster signature --juniper alternate
```

Override the full profile through `--profiles profile.json` containing `{"schema":"scp.r009.morphology_profile.v1","actors":{...}}`. Include both actor keys and all bounded numeric controls; see `DEFAULT` in the module. Never resculpt or bake an external source onto this public original-synthetic lineage.

## Fairy Tail costume references — design selection, NOT an imported asset

Use character costume photographs and credited reference artwork only as **visual study**. Author original fabric patterns, shapes, surface elements, materials, skin weights, and topology; do not import series meshes, logos, texture sheets, or trademark marks into this public-original track. Official character roster: https://www.tv-tokyo.co.jp/anime/fairytail2015/chara/

1. **Natsu Dragneel — high priority for Aster/Master:** sleeveless vest or long asymmetrical tunic, contrasting trim, broad wrapped scarf, loose cropped pants, belt, and open footwear in the series. Original design candidate: `aster-travel-vest-v1`. Implement a *new* sleeveless mesh cut and separate scarf simulation/control, not an existing jacket recolor. Check clavicle/armpit intersections and shoulder rotation clearance. Reference: https://fairytail.fandom.com/wiki/Natsu_Dragneel
2. **Gray Fullbuster — lowest-risk first functional garment:** fitted or layered light coat/shirt, dark trousers and boots, wrist and neck accessories. Original design candidate: `aster-mage-jacket-v1`; easiest pattern adapted from existing coat/long trousers, with distinctly authored collar, hem, front opening, sleeve options and fitted masculine silhouette. Reference: https://fairytail.fandom.com/wiki/Gray_Fullbuster
3. **Jellal Fernandes — later physics/cloth workcell:** layered high-collar shirt under an open long dark coat, belt, narrow boots and articulated flowing hem. Original design candidate: `aster-high-collar-coat-v1`; do not promote before coat-panel self-collision/wind/foot clearance tests. Reference: https://fairytail.fandom.com/wiki/Jellal_Fernandes
4. **Juniper — separate original feminine-mage cuts:** fitted waist jacket, layered tunic/skirt or shorts, independent belt/pouch and boots; optional dress, scarf, and longer hair complements. Favor articulated layered garments over clothing fused to the skin. Lucy Heartfilia is an example of feminine wardrobe variation within the same series, not a source asset imported here.

**State distinction:** The preceding costume concepts have **not** been meshed as new garments in this workcell. Parent #292 still only has same-cut alternative color variants; marking these references as completed clothing would be false. Source-new garment patterns are a separate bounded child engineering batch.

## Required visual, motion and custody exits

- Render front / 3-quarter / side and full-body neutral-pose before/after contact sheets with a fixed calibrated camera; pass independent human review (none yet).
- Verify jaw/brow/chin silhouettes; chest, waist, hip transition; skin-to-garment clearance, facial eye/nose alignment, and scalp coverage. Underbody protrusion is failure.
- Recheck 72 animation frames and all 35-joint weights with two viewports; detect skin breaks, clothing intersections, foot skate, clipping and contact discontinuity. Skeleton preserved is not a motion-quality pass.
- Keep biological/anatomical and outfit-fidelity verdict **UNKNOWN** until independent native visual evidence, not just a passing JSON/GLB unit test.
- Code, profile spec and reproducibility receipts stay in Git/DLE; original and rendered GLB/BLEND/MP4/PNG derivative binaries belong in the owner-private Drive R009 artifact store after full-byte SHA readback. Avoid private Drive locators in public CI.
- No modifications to protected Naomi/Alison, default main, existing rights review, release, merge, or CPE gates. First RED retained and attributed, no waiver-on-green.
