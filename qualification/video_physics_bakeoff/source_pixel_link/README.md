# Synchronized synthetic geometry → H.264 pixel witness (RDT&E)

**Public Visual QA DLE #150.** Independent improvement over prior [six-case geometry/pixel arbitration #365](https://github.com/SemperSupra/stable-character-pipeline/pull/365), which correctly identified that its pose source and videos were not coupled.

This workcell renders **the same exact source-observed 3D hip/knee/ankle positions** to deterministic colored joint fiducials and gray segment lines through a calibrated orthographic projection. It encodes 12 original frames to H.264, independently decodes their real RGB bytes with FFmpeg, detects red/green/blue keypoint centroids from the decoded pixels, and compares them frame-by-frame to the source projection. It also runs the *independent* native geometry inspector pinned to source SHA `bcccffbc016b980974fb46397e6eaa6e6f6d0b45` to determine knee-bend polarity.

**Two independent original-synthetic hypotheses:**
1. Valid joint sequence: geometry PASS, decoded pixel/source correspondence PASS, fail-dominant combined PASS.
2. Reversed-knee sequence, swapping ankle bending polarity in late frames but retaining the shank length: geometry FAIL, corresponding source↔decoded pixel alignment still PASS (the render truly shows the reversed joint), overall FAIL.

**First falsifier:** decode the *reversed* H.264 video but compare against the *clean* source 3D joint sequence; pixel source correspondence MUST return FAIL instead of inferring validity from geometry and a video that are not the same scene. Missing color markers, nonfinite geometry, malformed frame count and an unrecognized modality are hard errors rather than UNKNOWN. Twelve stdlib tests cover source determinism, camera calibration, marker alignment, actual native H.264, stale source and fail-dominant arbitration.

Every receipt reports the immutable source code and judge digests, calibrated projection, exact input 3D source SHA, actual encoded/decoded video SHA256, individual pixel residual errors, independent geometry verdict, late reversed-knee findings and stale-source negative test. All original clips and JSON are uploaded as public research artifacts; no checkpoint, identity, private footage or secret material.

**Scientific limit:** The synthetic joint markers are *schematic fiducials*, not anatomical silhouettes, learned image-derived human pose, dynamic balance, gravity, textured rendering, biological leg articulation or a real person. This validates that **the video really corresponds to the source joints**, not that the source joints are biologically convincing or character-realistic. Product/identity/rights release gates remain HOLD.

Fresh public Ubuntu VM only, ephemeral FFmpeg install, original rights-clean fixtures and standard-library Python, source-exact independent public judge checkout. No persisted services, `~/.local`, private paid Actions, GPU/TPU quota, Agent Dispatch, cross-organization token or build-host taint. Draft/unmerged and native CI evidence required before research qualification.
