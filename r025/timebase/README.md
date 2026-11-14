# R025 — imported action timebase contract (source-safe)

Independent synthetic Go validator based on the local actor's R009 #23 terminal #6875190112, not a reproduction of that private artifact.

Checks **two animation slots, 126 F-curves each, 72 keys per curve**, pinned 12 fps scene 0–71, a uniform 2-frame stride on imported action keys, and source-preserving reversible retiming to a 1-frame stride. Retimes all keyframe X positions and Bezier handle X coordinates, not pose values. Negative controls cover missing curves, mixed stride, scene FPS/frame-range drift and forged timebase.

**Boundary:** A source hash is only caller-declared; actual clip/key provenance, Blender action-evaluation behavior, modifiers, IK, pose/world-space alignment and contact cannot be independently attested by a synthetic key transcript. Do not publish local ASTER/JUNIPER action curves or proprietary geometry. No physical contact, cinematic or release PASS; source-local actor must independently cold-open and compare actual evaluated scene.

Source rights: project-original synthetic only. No A001 fitting, protected source transfer, owner merge, canonicalization or release. Independent of active local actor worktree and existing public #501–#505.
