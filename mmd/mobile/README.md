# W21 — reproducible original-source iPhone visual evidence

**Authority:** [public MMD DLE #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19), [draft PR #41](https://github.com/SemperSupra/stable-character-pipeline/pull/41), stacked against unmerged draft MMD base PR #20. Research-only, source rights-clean, $0 public GitHub-hosted CPU. No merge, release, deploy or automatic publication. This is an accessible *diagnostic media subgate*, not proof of production human characters.

## What creators can actually watch on an iPhone

- `original_31frames_looped_iphone.mp4`: **960×720 H.264 yuv420p**, 93 decoded frames, **3.1 seconds**, made from the original **31 consecutive genuine Blender renders**, repeated three times for legible observation. The object is a self-authored orange diagnostic triangle and not a real person's gait.
- `g7_g9_real_keyframe_slideshow_iphone.mp4`: **1080×1920 portrait H.264 yuv420p**, 144 frames, **6.0 seconds**, showing source-authored G7 articulated ribbon and G9 2-target morph grid at **only actual Blender frames 0/15/30**. Frame-hold visuals do **not** interpolate new mesh motion; they are three photographed original states.
- `phoneframe_000.png`, `phoneframe_001.png`, `phoneframe_002.png`: full portrait screenshots from the corresponding real source renders.
- `mobile_capture_receipt.json`: hash of every original source clip/render, output SHA256, codec, chroma format, frame counts/duration and semantic limits.

**Access difference:** GitHub Actions artifact ZIP provides reproducible custody but is not an in-app iPhone streaming link. For direct iPhone viewing this ChatGPT session downloaded and independently verified the exact CI artifact; it supplies ordinary playable `sandbox:/mnt/data/` MP4 and PNG links. These session links are not durable GitHub releases or public external URLs. To regenerate later rerun the workflow against pinned sources; do not publish arbitrary external models.

## Verification performed

[Actual public Actions PR run 40554134719](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40554134719) **COMPLETED/SUCCESS**. Used exact preexisting original G4, G7 and G9 [run 40451441477](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40451441477)/[G9 run 40455150395](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40455150395) source artifact references; all **seven** original MP4/PNG SHA256s were compared before any conversion; independent ffprobe verified both H.264 yuv420p outputs, even pixel dimensions and 93/144 decoded frames. GHA artifact **12755493153**, ZIP SHA256 `d6a95d5e10c9d1df9e6885c4aa0082b5d2fab2893cfbdbe98812a97400c08323`, standard 14-day retention. Chat session downloaded the ZIP and independently checked output stream metadata + output digests `3d1da9b33af0c8794a264ad6f8dff9fff32709204041b419c81206257e2d1242` and `b244d2d0551e72e982b8f58215096d57474c6fc545ff30bb5f3649b9f18b53d5` against machine receipt. No metered services.

## Audience contract

- **Human:** portrait screenshot, phone-tappable MP4 (H.264 Main/Baseline codec family, yuv420p and faststart), clearly labeled original fixture vs production character. Precise capture limitations, no false 'animated human' claim.
- **Automation:** [workcell workflow](../../.github/workflows/mmd-w21-iphone-media.yml) and [portable source generator](make_preview.py). Exact source hashes and ffprobe codec/frame assertions; repeatable failure for missing or nonmatching source evidence. Runner bounded to 12 minutes, artifact 14 days, zero-cost CPU.
- **Agent:** same manifest `scp.mmd.w21-mobile-capture.v1` with separate `PASS_PHONE_COMPATIBLE_H264_FROM_GENUINE_SOURCE_RENDER_BYTES` vs **NOT_TESTED** visual realism, native Babylon render, arbitrary MMD rights. No action can silently merge, publish or override CPE decisions.

## Next work-plan baton

W21's **mobile evidence-format reproducibility subgate passes**; this does **not** close W21 overall runner hardening/rights budget/source dependency audits. For every future character, flora, fauna, machine and interactive scene workcell, define required source frames, MP4 H.264 yuv420p + faststart and PNG stills, mobile test and source rights in its admission manifest. GHA ZIP is evidence custody; direct user links need conversation-scoped controlled extraction or a separately authorized hosting surface. No automatic final publication. W04 real PMX/VMD/Babylon runtime remains a separate qualification path, not depicted by these Blender visuals.
