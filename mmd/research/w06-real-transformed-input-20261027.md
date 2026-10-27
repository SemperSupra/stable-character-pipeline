# W06 actual transformed source VMD — verified $0 public runtime

Authority [DLE #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19), separate unmerged draft [PR #64](https://github.com/SemperSupra/stable-character-pipeline/pull/64) based on draft W04 PR #34.

Original rights-clean G10 VMD SHA256 `e61ae2953c6cd34904fec2c59ae95fe64ed043ce0cde93e1c3d5db3d12ed149c`; pinned native MMD Tools serializer/reloader scaled controller VMD translation by **0.75** at keyframe 30, producing actual new file SHA `fe9906539b7521944a2c6d88097ef213ac917366ca965dd8265c2e7f2a95aad0`. Pinned actual upstream Babylon MMD and BabylonJS NullEngine evaluated original and generated VMD on all **31** frames; Go stdlib independently checked per-frame goal scaling, unchanged original hip and ankle-target bound, and rejected three adversarial mutations.

[Native SUCCESS run 40597318912](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40597318912), head `204a0818932a80793305011a57d447b43f2ff8e9`, job `122516405983`, proof artifact **12777271956** SHA ZIP `bee6c8cb5daccb3ff93bbb604cfe48f5685416486e68213095f1963b6f0b8e49`. Measured maximum 31-frame goal transform error **1.4901161193847656e-8 original PMX source units** and unchanged hip max error **0**. All bounded source-gate checks PASS.

Not qualified: actual MikuMikuDance application's CCD solution equality, arbitrary motion transformations, cloth/Bullet/contact, human body or physical-meter scale. W06 canonical task remains READY for independent review. Next: additional source transforms, adversarial strength/exhaustive design of experiments, cross-engine physical and temporal precision. No merge, release, deploy, or private source transfer.
