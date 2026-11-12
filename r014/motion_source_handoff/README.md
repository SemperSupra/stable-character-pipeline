# R014: reuse existing human motion-source research, not another global sweep

**Authority:** [private R014 #138](https://github.com/SemperSupra/stable-character-pipeline-private/issues/138) for the MHR human, separate [R009 #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23) for protected video and [R015 #141](https://github.com/SemperSupra/stable-character-pipeline-private/issues/141) for semantic morphology.

## Existing research to consume without duplication

- [Source discovery #349](https://github.com/SemperSupra/stable-character-pipeline/issues/349): English, Chinese, Korean, Japanese, German, French, Spanish source and concrete motion/media sweep, including CMU mocap, AIST++, DanceDB, Chinese DAISCH-MOCA, historical motion. Not exhaustive of all languages.
- [Shared motion/admission #29](https://github.com/SemperSupra/stable-character-pipeline/issues/29): source rights, corpus lineage and train/test split admission, donor data S0–S6.
- [MMD motion #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19): source-backed ASF/AMC/BVH/retarget; permissive DFKI anim_utils, MMD serializer and native Blender/MMD qualification.
- [W07 #84](https://github.com/SemperSupra/stable-character-pipeline/issues/84): W07 Go source-neutral scp.walk_motion.v1 is limited to **72-frame/12fps/2D self-authored synthetic dual-actor contact**. It is NOT a general 3D ASF/AMC mocap IR; do not silently claim that it can carry all captured joints and native timestamps.
- [R009 real CMU upper-body donor](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23#issuecomment-6748091054): source-authored protected Blender prototype used genuine CMU 07_01 WALK upper-body directions layered with a separately authored ankle/contact controller. This research does NOT re-export protected media or artist identity, and has not obtained the source recording bytes.
- [Actual R014 MHR pelvis-corrected gait #458](https://github.com/SemperSupra/stable-character-pipeline/pull/458): 169 source Go frames, real 18,439-vertex MHR evaluated mesh and 126-bone rig, accurate world ankle target position; foot/toe contact and pelvis motion still unnatural. Reuse it as a target benchmark.

## Primary CMU source and technical restrictions

Official CMU Graphics Lab page https://mocap.cs.cmu.edu/ permits research use and embedding motion in commercially sold products, but prohibits selling the raw motion directly **even converted**. Its toe/hand joints are noisy and fingers/thumbs were NOT captured—they are editing conveniences. CMU ASF/AMC format notes https://mocap.cs.cmu.edu/info.php document ASF unit length 0.45 and conversion (1 / 0.45) × 0.0254 metres per source coordinate when actual header verified; AMC frame indices do not by themselves prove an authoritative source FPS.

Official subject07 index https://mocap.cs.cmu.edu/subjects/07/ lists 07.asf and 07_01.amc. In this bounded experiment no actual ASF/AMC bytes were obtained, no file SHA was computed and no private or public source venue was approved; individual exact-take and actor/data rights stay held.

## Reusable target approach

1. Retain pinned 169-frame Go contact and actual MHR source animation as baseline, and preserve its old negative controls.
2. Only on a separately authorized private workcell, process *genuine* acquired CMU07_01 exact source through already owned ASF/AMC and DFKI or Blender translators; verify clock, rest axes, skeleton length scale, FK and joint lineage.
3. Source real hip/pelvis/spine/shoulder/elbow style from the recorded motion, but do not trust noisy source toes or synthetic fingers. Contact must carry OBSERVED / ESTIMATED / UNKNOWN provenance, never be relabeled by motion word or rig.
4. Target native R014 MHR and separately qualify source-driven pelvis/upper body, trajectory/contact and dynamic toe/foot constraints, across held-out body morphology, 3D mesh folding, pose ROM, temporal motion and cinematic visual review.
5. Preserve human operator, CLI automation and agent inspection/receipts; R014, R015, R009 and source-owner DLE responsibilities stay independent.

## Executable bounded source handoff

This branch supplies a **Go 1.23.2 stdlib-only source identity, exact-hash, contact/clock/rights admission guard** with a four-record reuse catalog; hostile tests deny missing source, fabricated source hash, unreliable CMU toe/observed-ground labels, untrusted publication, duplicate actor, and wrong 3D-vs-W07 IR assumptions. CI uses two independent $0 disposable public runners and tests metadata only; it never downloads or republishes original external motion or model weights.

CMU07_01, AIST++ and DanceDB are metadata-only and HOLD here. The Go source programmatic 169-frame proof is pinned to SHA256 44d8ebb4bee9a01f522a92ff4377c4cc66c9b19df835bb4b6a1e2a847179fd56 and cannot be mislabeled natural recorded gait.

**Release disposition:** fail closed — no real donor capture retargeted in this workcell, no production-quality foot roll/soft tissue/face/hands/skin/hair/anatomical coverage or cinematic 4K qualification; all PRs remain draft/unmerged.
