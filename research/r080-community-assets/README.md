# R080 — source-safe CC0 MakeHuman clothing archive qualification

Purpose: independent public/free-tier batch to obtain real source manifests and hashes, not to pass protected Naomi/Alison characters.

Official catalog records (CC0 category):
- https://static.makehumancommunity.org/assets/assetpacks/shirts01.html: tube top and camisole
- https://static.makehumancommunity.org/assets/assetpacks/pants01.html: jeans shorts and casual trousers
- https://static.makehumancommunity.org/assets/assetpacks/shoes01.html: platform boots and flats

The Python stdlib workcell checks official HTTPS redirect, compressed/uncompressed byte quotas, archive hashes, ZIP path traversal, duplicates, symlinks, CRC and garment inventory. The public runner retains only metadata receipts, not source asset images, native models, textures or original reference media. Source catalog rights are `CC0`, but `per_file_license_admitted` is hard-false until per-file rights and actual MPFB fit/weight evaluation. On any failure retain the first RED and do not silently replace with guessed garments.

Next: source-licensed exact subset import onto both synthetic female MPFB bodies with independently verified clothing armature bind, silhouette, foot-ground contact and motion. Private Naomi/Alison source fit remains under separate source-operation authorization and original source hashes. Neither synthetic lookalike nor archive listing is MVP acceptance.

Reproduce source tests: `cd research/r080-community-assets && python3 -m unittest -v test_audit`. Three real pack downloads run in separate public GitHub Actions jobs with no private GHA minutes and no paid models. Keep PR draft/unmerged, DLE holds intact.
