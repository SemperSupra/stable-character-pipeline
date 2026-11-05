# Native Shetland leg local-axis corrective A/B

DLE: https://github.com/SemperSupra/stable-character-pipeline/issues/293

Source owner parent PR #294 frozen `1f2febbd28d508d1c3d9f2a644f861d634f65a9d`. Same source code and 26-joint rig, change only `pose.bones[...].rotation_euler[1]` (longitudinal local Y shaft twist) to `rotation_euler[0]` (candidate cross-axis hinge). Do not assume physical correctness based on this change. Independent observer is #298 exact `7e03073f14df7e6103a30a96b8430ccb988914c8`. Public GHCR actual native two-source build, 48-frame four-hoof evaluated geometry report and comparison. If hypothesis fails, preserve as scientifically useful first run and pursue rest-axis mapping / world-space IK. Output remains source-original synthetic, separate from user's 62 MB v1 pack. No private runner, protected photo upload, merge, release, deployment or CPE.
