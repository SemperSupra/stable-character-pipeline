# Visual QA W2A — independent temporal evidence, draft research

Authority: [Visual QA DLE #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150); stacked on original public-only visualqa PR #152 at exact source head cb8de12d929ed5e118b1fef0d835132ecf6deb2c. The existing fail-closed L1 video test remains **unchanged**.

Go/Blender source data, actual FFmpeg-decoded grayscale images, and native video binary are observed via **separate inputs and hashes**. For each of seven sampled timeline positions, the observer compares independent Blender evaluated hip/knee/ankle displacement to decoded per-frame mean absolute pixel changes. It emits all 71 real frame transition statistics and source-pixel intervals. Intentionally invented research thresholds produce *suspect intervals* only, never anatomical or video acceptance.

Negative tests cover actual 24-frame moving and black H264, near-identical but byte-different frames, altered source/video SHA, and duplicated source time. All runs are source-original on standard free public CPU GitHub Actions; independent native forward/outward jobs retain artifacts for 3 days. No private character media, protected hardware, model API, paid runner, release, merge, deploy or CPE promotion.

Exit from W2A research is a JSON receipt with status `OBSERVED_RESEARCH_ONLY`. If the original W16-C2 video still violates FFmpeg freeze thresholds, its original L1 receipt remains `FAIL`. A green W2A workflow does **not** override that failure.

Next: compare source-intended and camera-projected motion to optical flow measured from actual surfaces, preserve lens/occlusion and reset negative cases; qualify the thresholds against independently adjudicated natural and bad clips. Research outputs and failures -> Git/DLE; short-lived binary media -> private Drive only with exact full-byte integrity and approved rights. 
