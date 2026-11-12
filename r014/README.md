# R014 source and weight provenance review: MHR

This independent public workcell checks the upstream MHR model-asset ZIP against GitHub's published v1.0.1 SHA-256 digest and extracts only LICENSE text and a filename/size manifest. No model weights are uploaded in job artifacts or included in this branch.

Source pin `facebookresearch/MHR@85fc2cbaf77f606e41346cb791d8ad96a75e1a4b`; assets `v1.0.1/assets.zip` expected SHA256 `e4f4f205cd87c0fa106577ba1de4fc763e4eb197c924461d2ef7e6944e9d6b94`. The source repo's Apache-2.0 file and embedded model-asset license are separate evidence. No rights admission occurs automatically.

Two bounded public-runner jobs independently inspect source metadata/compilation and archive license/integrity. Both are research-only, no private R002 or protected likeness files, no secrets and no release. Private product authority: https://github.com/SemperSupra/stable-character-pipeline-private/issues/138

No merge/model promotion unless a human in command reviews the license rights and full inference qualification.
