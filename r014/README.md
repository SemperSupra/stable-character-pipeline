# R014 version-pinned reproductive reference anatomy census

This workcell uses two upstream **reproducible, independently versioned, publicly released anatomical reference** projects. Neither is an R014-ready human skin, body shape parameter or physical tissue solver.

- Male reference: `organui/prostate-3d@204c67a54226a19868abd0a5e8449a7f82827bf9`, 13 grouped structures, BodyParts3D / Anatomography. **Model** CC BY-SA 2.1 Japan (not MIT). Useful for glans, testes, urethra, prostate and other internal reference, NOT accepted external scrotum/penile skin/foreskin.
- Female reference: `organui/uterus-3d@404a6039b2d667e2b4e08ae71d4964cd9b963cf1`, 27 grouped structures, HuBMAP HRA. **Model** CC BY 4.0 (not MIT). Useful for vagina, cervix, uterus and adnexa, NOT accepted clitoral/labial/vestibular external anatomy.

Both upstream **applications** are MIT; their underlying models explicitly are not. License decisions must remain per source artifact. The CI reads pinned model bytes and source manifests, validates exact SHA256, structural GLB metadata and core anatomical IDs, emits machine receipts only, and records unqualified external anatomy.

DO NOT merge either dataset into public MPFB CC0 base meshes without a scoped licensing decision, source/geometry alignment and independent anatomical review. Attribution or ShareAlike obligations can attach to distributed derivatives. For a video pipeline, external anatomical surface articulation, skin UVs and realistic dynamics are still separate design work.

Private product authority: https://github.com/SemperSupra/stable-character-pipeline-private/issues/138.
