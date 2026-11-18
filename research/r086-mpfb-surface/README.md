# R086 — Official MakeHuman system hair, skin, eyes and face-surface source qualification

Independent follow-on to R014 native lookdev and R080/R082 wardrobe; separates appearance/source rights from the R083/R084/R085 motion critical path. **No protected Naomi or Alison mesh, photograph, skin or source-specific measurement** enters public free-tier GHA.

Inspect the official MakeHuman community `makehuman_system_assets_cc0.zip` from `files2.makehumancommunity.org` only after SHA-256 matches `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107` (previous exact R014 custody). Enforce finite download size, ZIP CRC, no path traversal/duplicate/symlink, bounded compressed and expanded sizes, and separate read-only SHA/license-header census for `.mhclo` and `.mhmat` control files. Inspect seven category inventories: hair, eyes, eyebrows, eyelashes, skins, teeth, tongue. Record selected long01/short01, high-poly eyes, lashes, eyebrow001 and young-female skin provenance only as **candidates**.

A catalog-level CC0 label alone does not automatically admit embedded material/mesh textures. If an embedded header contradicts that license (as observed in other clothing packs) retain a typed rights conflict; missing explicit per-item license is HOLD. Do not copy skin textures or hair geometry into public git or upload package model/texture assets; public artifact is small JSON receipt only.

After source qualification, next independent real MPFB workcell: two adult fictional bodies, approved hair/eye/eyelash and skin material, vertex/ribbon rig weights, front/back/profile/face turntable and roughness/SSS/eyeball shape tests; produce actual same-scene source-rig attachments. Do not claim exact face/skin resemblance to Naomi or Alison, or medically realistic tissue, without separately admitted private source-bound multiview targets, VLM/geometry critic and owner approval.

Run locally without network: `cd research/r086-mpfb-surface && python3 -m unittest -v test_system_asset_census`. Run real official source audit on public standard free-tier GitHub Actions. Keep all builds draft/unmerged and release HOLD.
