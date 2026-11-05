# 48-frame 24fps Shetland → exact 48kHz WAV → H264/AAC join

DLE [#293](https://github.com/SemperSupra/stable-character-pipeline/issues/293).
Public zero-dollar standard GitHub Actions only. Three immutable independent sources:

- Source-original walking geometry 48 frames: [IK #302](https://github.com/SemperSupra/stable-character-pipeline/pull/302) `1b0a12da753ad662ec5b21f8d1aad73fba3224d9`.
- 48-frame gait event clock: #296 SHA `497203219d035bafd72be2d4a34786c1396526ff`; one 2-second cycle yields 4 impacts frames 0,12,24,36 (48k samples 0,24000,48000,72000).
- 48kHz deterministic synthetically generated sand Foley: #297 SHA `630c31408d3b76575d361a51770b9a336393fd76`.
- Independently reimported exact GLB rendered PNG-to-H264 48f black playback from #304 public run 42117671062, verified MP4 SHA `16205b172604ec86c389b7bdc8615ed45b0fb4f9882e5a18f266428386000a99`.

The workflow downloads the already public artifact by authenticated GitHub Actions read, **not owner Drive**. Fails closed if the video origin/hash/camera or clock differs. Does not capture user source photos/videos, private rigs, vendor audio, or any non-CC0 assets. Output is an *engineering AV timing witness*, not actual hoof strike observations, horse vocalization, anatomical gait correctness, or final sound mix. Rights/merge/release/deployment/CPE holds intact.
