# Exact horse-source admission workcell

Owning DLE: https://github.com/SemperSupra/stable-character-pipeline/issues/293

This workcell downloads exactly one upstream Mesh2Motion horse animation GLB at pinned commit 935cfb82d14223d7631d04ba2bb14e2feb8ca517, checks byte count and Git blob SHA-1, parses the glTF skeleton and action manifest with independent stdlib code, and imports into official SHA-verified Blender 4.5.15 running in the published GHCR bpy dependencies image.

Source art claims CC0 in the upstream source repository license; code licensing is separately MIT. Candidate is not yet imported to our Shetland rig, not accepted as anatomically correct, and not redistributed as a released asset. The native source import still/photo are technical validation only. Do not upload owner photographs, locally generated v1 pack or protected character data to public Actions.

Three-audience contract: humans review action list/image, automation reads machine JSON + hashes, agents use deterministic one-source check/decision labels. Any missing source, changed hash, invalid GLB or Blender import failure stops the workcell. No direct main merge/release/deploy or CPE.
