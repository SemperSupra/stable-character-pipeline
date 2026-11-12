# R014: actual leg IK target-space diagnosis on real MHR skeleton

This experimental workcell is **independent of the failing 169-frame gait attempt** ([#446](https://github.com/SemperSupra/stable-character-pipeline/pull/446)). It operates on the identical native MHR v1.0.1 source LOD1 with 18,439 skin vertices and 126 rig bones, with the original model checksum and Blender 4.5.16 pinned on disposable public runners. No private input or likenesses.

R014 #454 independently established that pure root motion through the armature object preserves the skin, whereas a numerical .2 root-pose-bone translation gives only .002 world units due source hierarchy scale. Thus we must isolate IK/bone target interpretation, not simply edit the model-root gait speed.

Each left/right independent public GHA job measures six true Blender-IK configurations: two owners (lowleg two-bone chain; foot three-bone chain), each with target (i) at that owner's rest tail, (ii) shifted +0.04 native-world units from that tail, and (iii) at the foot head / nominal ankle. It compares original knee/ankle/tail positions and parentage, owner-tail targeting error, actual ankle-head residual, all evaluated skin displacement, 36,874 fixed polygon-fan triangle flips/collapse, reversibility after removing the constraint and true held native file plus image. Do not treat bone display tails as anatomical joint centers without measuring them.

The numerical outcome will distinguish incorrect target space, wrong owner/end-effector bone, short FBX control handles, and fundamental IK solver deformation. A green runner only confirms the experiment completed. The status is always HOLD_STATIC_IK_NOT_GAIT_READY. Nothing is considered walking, foot lock, ground collision or biomechanics without an independent complete 169-frame acceptance run.

The next corrected 169-frame run must use whichever source-native chain passes zero-tip targeting, a source-proven reachability bound, correct body/rig root hierarchy, native LOD geometric integrity, toe/heel contact and no runaway vertex excursions; test neutral and held-out morphology separately. If all cases fail, make new analytic bone-space joint rotations in a separate research branch instead of forcing the imported FBX IK constraint.

Authoritative DLE: [R014 private #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138). Draft/unmerged; no release or main merge; R009 video remains HOLD.
