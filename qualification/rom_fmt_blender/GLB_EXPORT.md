# ROMFMT V2 D - actual Blender skinned GLB exporter test

Authority: [ROMFMT #175](https://github.com/SemperSupra/stable-character-pipeline/issues/175), stacked on .blend native draft #177 and independent GLB metadata draft #176.

On free public CPU, construct an original synthetic two-bone Blender rig with genuine skin weights, native rotation and IK limits, and source annotation custom properties. Run Blender's installed real glTF exporter with extras enabled and inspect the actual produced GLB binary. Report explicitly whether asset/mesh metadata survived, whether the real skin joint exists, and whether the specific bone node retained the source annotation. A missing extras field is a fail-closed preservation defect, NOT unlimited anatomical ROM.

Only synthetic source limits are admitted. Exporting glTF skin + extras never means Blender's IK / rotation constraints are enforced by an external game engine, nor establishes natural human/animal anatomy, contact, velocities, loading or release. The native test intentionally strips exported annotation to demonstrate a negative control.

Source and small evidence: Git drafts/DLE. Real GLB/.blend original media: private Drive only after full binary SHA custody. No private actors, paid cloud, merges/releases/deployment or CPE promotion.
