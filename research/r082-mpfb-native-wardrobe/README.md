# R082 — original MakeHuman garment-fitting vertical slice (source-safe)

Parent: R078 MPFB official 163-bone AsterOriginal/JuniperOriginal (#640). Independent sibling: R080 official CC0 asset pack census (#641). Source protection and private Naomi/Alison reference fit stay on private R079 #190 / R009 DLE #23. This workcell is a **draft/experimental** native Blender test; no protected asset is transferred to public runners.

Exact packs (verified on free public GHA): Shirts 01 SHA a5a723b0e84a109bb190fcfeac7f1de4138d875da3e30fe5b3340eac9f38bcd3; Pants 01 SHA e4e0ec60db34f279be291a83cfd7b342a7c5cf09bb7676682a5f39f4f6ac4ad9; Shoes 01 SHA ded3f70428505eabbf1f6d7b5f61196a7366ef20757103d276ad0ed336c35ada. Each item is imported only if its **own MHCLO header explicitly says CC0/CC-0**; no catalog-level blanket attribution. AGPL3-holding tube top and platform boot are rejected and remain rights-conflicted.

Selected first safe approximations:

| Fictional subject | Top | Pants | Shoes |
|---|---|---|---|
| Aster | toigo_bodice-style_top | toigo_harem_pants | toigo_stiletto_booties |
| Juniper | toigo_camisole_top | toigo_wool_pants | toigo_ballet_flats |

Colors are **original procedural materials** and not licensed source textures. This is a wardrobe-mechanics trial, not a verified reference outfit match, and the garments above are intentionally not asserted to be screen-accurate replicas.

Execute public CI: 10 hostile source-only tests, pin official upstream Blender MPFB, re-create original two females/72f, verify archive hashes and per-MHCLO license text, call actual HumanService.add_mhclo_asset(), require armature attachment and evaluated clothing deformation in pose, save source-bound native .blend, fresh-process reopen, render three stills; retain small JSON hashes/evidence only.

Hold gates: silhouette/fit collision, cloth flutter and garment self-intersection, sneaker/heel contact and gait, actual reference likeness/appearance, photoreal skin/eyes/hair, exact-source rights, final 144f integrated outfit+secondary-motion film and owner feedback. No merge or release on narrow tests.
