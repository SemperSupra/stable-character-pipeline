# R014 facial expression control crosswalk — source-only RDT&E

This independent bounded public lane extracts **actual names** from pinned official MHR and MPFB source rather than guessing how shape indices correspond to facial animation controls.

MHR identity morphs occupy source shape indices 0–44 and 72 facial coefficients follow at 45–116, giving 117 exported non-Basis shapes in LOD1 FBX. MPFB exposes 52 ARKit-style face units; **`faceunits01` is an additional optional asset pack** and is not installed in R014's baseline.

The crosswalk provides narrowly scoped semantic suggestions, NOT physically calibrated amplitude curves, animation transfer, FACS action-unit certification, or proof that both systems implement the same motion. This requires subject-independent expressive video QA and exact asset-pack rights and source pinning.

No identity assets, source model weights, protected footage or audio are used. Issue authority: https://github.com/SemperSupra/stable-character-pipeline-private/issues/138 .
