# W04 — pinned third-source Babylon MMD parser, real rights-clean fixtures

**Authority:** [Stable Character MMD DLE #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19), standalone candidate [draft PR #34](https://github.com/SemperSupra/stable-character-pipeline/pull/34) from **unmerged** public MMD draft PR #20. Do not merge, release, deploy, publish community models or propagate private identities. No unapproved CPE research/policy changes.

## Discover

[noname0310/babylon-mmd](https://github.com/noname0310/babylon-mmd) is a genuine open-source MIT-licensed MMD loader/runtime project; authoritative upstream pinned **commit `ccb750db2998ed1067017eaf67f3fc987cfba6f8`** (public main observed 2026-10-27). Source-level inspection showed:
- `src/Loader/Parser/pmxReader.ts`: real `PmxReader.ParseAsync(ArrayBufferLike)`, native PMX version/header/geometry/bone/vertex/morph/material/physics parser.
- `src/Loader/Parser/vmdObject.ts`: real `VmdData.CheckedCreate(ArrayBufferLike)` and `VmdObject.Parse`, source VMD bone/morph/camera keyframe parsing, shift-JIS text semantics.
- Distinct `PmLoader` and `VmdLoader` build Babylon scenes/animations and MmdRuntime solves poses. These **were NOT executed by the parser-only evidence**. The project also has optional optimized WASM/Bullet physics. We must keep source parser evidence separate from renderer and solver claims.

Reuse existing TypeScript parser without inventing a PMX spec parser or requiring project's full Rust/WASM build. Sparse-checkout the exact upstream parser source only, execute it with pinned MIT `tsx@4.20.6` on $0 GitHub-hosted Ubuntu CPU. The thin test adapter is tooling, not a replacement engine.

## Actual source / evidence

| Original self-authored fixture | Native PMX SHA256 | VMD SHA256 | Babylon source parser outcome |
|---|---|---|---|
| G10 original 4-bone synthetic IK PMX/VMD | `fadfc3cb3d365cdb4b0c4cc26652c2e831a02ec7da518caae9142dd711468583` | `e61ae2953c6cd34904fec2c59ae95fe64ed043ce0cde93e1c3d5db3d12ed149c` | PMX 2.0, **6 vertices/4 triangles/4 bones**, native **2 bone VMD keys** |
| G9 synthetic 2 vertex morph face PMX/VMD | `311e8da1c17d924ac40ed84a543a162c79b5ad7a19d5718a62072f8908757d42` | `b69a57beeffe067cf7a100cb45ac83259c05004ffda5c599da54b5fb5b60b663` | PMX 2.0, **16 vertices/18 triangles/1 bone/2 morphs**, native **6 morph VMD keys** |

The real parser independently rejected corrupt first-byte PMX and VMD signatures for both fixtures. It did **not** run a Babylon MMD scene loader, play the motion, solve IK, simulate Bullet or render an interactive view.

**Verified initial run:** [public Actions 40550350719](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40550350719) terminal **SUCCESS**, original source and native parser all matched expected counts/hashes, native job `122352069024` logs read. Output artifact `public-mmd-w04-babylon-source-parser-evidence` **12755201220**, ZIP SHA256 `045f16d0b5b8a0d808d186ea1dad7a5e633c2d7c51f9193f674be5eb75709769`, 14-day retention. Machine receipt `W04_BABYLON_NATIVE_SOURCE_PARSER` labels `PARTIAL_PARSER_PASS_FULL_RUNTIME_HEADLESS_NOT_TESTED` and two expected negative rejections. No external model/texture, runtime demo, unverified cloud GPU, billed runner or secrets used.

## Three audiences / gate interpretation

- **Human:** read this provenance/limitations and the exact native Actions logs to separate parser vs runtime motion qualifications.
- **Automation:** run `.github/workflows/mmd-w04-babylon-parser.yml` with pinned source/runner and inspect raw `w04-output/babylon_native_reader.json`; scripts are repeatable and reject source SHA mismatch/malformed native magic.
- **Agent:** same JSON verdicts, input SHA, upstream pin, fixture semantics, negative controls, `runtime_pose_evaluation:NOT_TESTED`. No automatic policy, rights or release changes.

**Next W04 baton:** qualify *real* `@babylonjs/core` NullEngine scene loader (if supported) with genuine PmxLoader+VmdLoader and synthetic G10/G9 source. Then run `MmdRuntime` physics-off with 0/15/30 source frames; inspect actual evaluated bone/world/morph states and compare to the independent converter/Blender with objective tolerances. Explore browser/WebGL playback only after headless source semantics; if Node NullEngine cannot support actual material or renderer APIs, document exact first failure and choose a free-tier headless browser renderer rather than silently substituting mock animation. Keep WASM/Bullet and native MikuMikuDance solver parity independent qualification gates.

**Disposition:** `W04_NATIVE_FORMAT_PARSER_SOURCE_PASS / W04_SCENE_RUNTIME_AND_3D_ANIMATION_NOT_TESTED / W04_CANONICAL_READY_REVIEW_HELD`. Draft PR #34 cannot merge automatically; W03 cross-reader glTF warning remains in draft PR #33, W02 Go proof in PR #30, and neither is automatically qualified by a parser-only W04 pass. W19/W20 blind CPE lane remains BLOCKED until authorized access and evidence.
