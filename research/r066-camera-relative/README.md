# R066 — camera-relative H.264 critic, source-clean qualification
**Authority:** [public Visual QA #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), [private R033 #168](https://github.com/SemperSupra/stable-character-pipeline-private/issues/168), [private MVP #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23). Use the canonical Way of Working; DLE = Durable, Legible, Executable. Research only, no owner promotion.

## Why this next batch?
R063/R064 VLM candidates produced one-sided direction labels (each 1/2 correct). R065 [draft PR #610](https://github.com/SemperSupra/stable-character-pipeline/pull/610) [GHA #43969432810](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/43969432810) independently measured absolute red-marker motion on encoded and decoded H.264 (RIGHT +138px, LEFT -138px, STILL 0px, missing target UNKNOWN). Absolute pixel motion conflates object movement with camera translation.

## Five independent source-original falsifiers
- **camera-pan-only**: red subject and static green fiducial translate +24px together; object-relative direction MUST be STILL, not RIGHT.
- **right-with-opposite-pan**: red subject +33px, reference -22px => relative +55px RIGHT.
- **left-with-opposite-pan**: red subject -33px, reference +22px => relative -55px LEFT.
- **missing-fiducial**: moving red with invisible reference MUST be typed UNKNOWN, nonzero exit; never invent camera compensation.
- **missing-subject**: moving reference with invisible subject MUST be typed UNKNOWN, nonzero exit.

All cases generate new original PNGs, **actually FFmpeg encode and decode H.264**, read back decoded frame pixels (not source PNG), compute red and green centroids, subtract reference delta, enforce camera and marker area/size consistency, and record exact source/decoded-frame SHA256. Parallel source-owner jobs run offline Go race/vet with 6-min bounds, public standard GHA only. Logs/receipts retained 3 days, no binary artifacts.

This is only a **translation-only single-static-green-reference** comparator. One fiducial cannot correct camera rotation, zoom, depth parallax, occlusion, subject tracking, non-rigid 3D anatomy, human motion, foot contact, gait or actual cinematic footage. Do not infer real VLM validity from passing these scripted fixtures. Other critic candidates must pass matched **held-out** frame/lighting/camera/occlusion DoE using numerical and provenance witnesses. No new scheduler, no third-party source or weight admission, private GHA, secrets, protected media, release or PR merge.

Reproduction: `go test -race ./... && go vet ./...` under `research/r066-camera-relative`; full actual decoded-video commands are in [workflow](../../.github/workflows/r066-camera-relative.yml). At authorship hosted status **NOT_OBSERVED** until GitHub run/job completion. Cite exact commit/run/receipt to existing DLE.
