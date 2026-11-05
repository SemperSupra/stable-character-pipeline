# Shetland GHCR Blender workcell (public-original source only)

Owning DLE: [#293](https://github.com/SemperSupra/stable-character-pipeline/issues/293). Context: original public R009 [#272](https://github.com/SemperSupra/stable-character-pipeline/issues/272).

This independent **draft qualification workcell** uses the documented Blender Foundation CI dependency image `ghcr.io/blender/runner-images/bpy:1.0.0` on standard **public** `ubuntu-24.04` GitHub Actions. The image contains Linux bpy dependencies, **not** Blender itself, so the workflow downloads the official Blender 4.5.15 Linux binary and verifies the published SHA-256 before running. It uses no local/sovereign resource or private GitHub Actions minutes.

`build_blender.py` produces **three procedurally authored 26-bone pony variants**: black/pink-halter, chestnut-white pinto, and cream-white, with polygon ribbon fur, sculpted UV-sphere body/leg elements, animated bone channels, native `.blend`, rigged `.glb`, and a rendered `.png` still. The independent stdlib `validate_outputs.py` rereads the actual GLB bytes and checks skin count, animation channels, skinned geometry, PNG dimensions, .blend magic, and artifact SHA-256.

**Provenance boundary:** these are newly authored synthetic derivatives used to exercise the public native production path. They are **not** the three ~38 MB v1 GLBs produced locally from the owner's supplied pony reference photos/video. No uploaded photo/video, person's likeness, private asset, other branch owner code, third-party model, or user Drive identifier is included. Native structural PASS alone will not be claimed as anatomical/visual/biomechanical acceptance or as byte-for-byte qualification of v1. Gait dynamics/foot contact/coat realism remain UNKNOWN pending independent image and motion review.

Run `.github/workflows/shetland-ghcr-native.yml` from an authorized public PR; inspect the archived GLB/BLEND/PNG/JSON outputs and retain first native failures in DLE. **No merge, release, deploy or CPE promotion is authorized by this workcell.**
