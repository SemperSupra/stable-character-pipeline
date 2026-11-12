# R014 MHR neutral actual-mesh tissue driver test

This workcell depends only on draft #405's **source-pinned native MHR bridge** and copies the exact `tissue_dynamics.py` controller from draft #410, blob `2f55179b3fb49cf203033fd09f72b5e86acebb73`. No changes to either parent branch or public main.

It creates two bounded Gaussian world-space spatial regions on the actual 18,439-vertex MHR LOD1 skin (one cheek, one abdomen), produces 4 signed morphs, animates from deterministic 240Hz integrated kinematics, saves and reopens native Blender source, exports GLB morph animation and renders a 1-second CPU technical preview.

These are **artist-control/motion plumbing tests only**. Region geometry is approximate, parameters uncalibrated, and it does not implement muscle layers, organ geometry, contact, deformation collision, tissue incompressibility, or cinematic realism. The experimental MHR mesh is neutral—not a validated male or female morphological preset. No private likenesses or asset packs are transferred.

Retain as draft, NO merge. Authority: https://github.com/SemperSupra/stable-character-pipeline-private/issues/138 .
