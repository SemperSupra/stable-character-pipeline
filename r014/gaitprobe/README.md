# R014 disposable Go gait controller research (not a digital human)

This workcell models step contacts, global root travel, start/walk/60-degree-turn/stop sequencing and analytic two-bone knee targets. It is **not** an animation of either current 3D human model, nor a gait biomechanics qualification.

It deliberately proves world-space planted-foot locking and bounded two-link IK against deterministic trajectories before any attempt to retarget to MPFB/Blender Studio/Meta rig. Leg proportions, motion, joint axes and appearance have not been anatomically validated. No FACS, finger, soft tissue, or sex-organs involved. Video is a simple wireframe diagnostic, not a person or photoreal video.

Run: `go test ./...` then `go run . --out /tmp/r014-gait`; optional `ffmpeg -framerate 24 -i /tmp/r014-gait/frames/gait_%04d.png -c:v libx264 -pix_fmt yuv420p /tmp/r014-gait/preview.mp4`. Go stdlib only, no persistent host dependencies required. Public free-tier GitHub Actions runner is preferred for reproducibility; follow the private R014 DLE.
