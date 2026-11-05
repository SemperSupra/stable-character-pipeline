# Agent reconstruction — candidate-only contract v0

Owner scope: public original synthetic equine #293 and original synthetic human #272; protected human #23 remains private and separate.

The reasoning actor proposes a hypothesis, evidence hashes, frozen baseline hash, exact operation and bounded parameter sweep. A deterministic controller validates the request. A separate verification step evaluates the candidate against held-out evidence. The controller never merges, promotes or changes the accepted model.

Allowed typed operations: shape.fit, rig.optimize, motion.fit, render.compare. No arbitrary scripts, downloads, private identities, or shell execution. Proposals are candidate-only, immutable and hash-bound. Classification: public_original_synthetic_human or public_original_synthetic_equine. All proposals must include strict resource bounds.

Mandatory dispositions: REJECT_PROPOSAL, VALID_PLAN_ONLY, REJECT_CANDIDATE, UNKNOWN_REQUIRES_INDEPENDENT_EVIDENCE, PROVISIONAL_FOR_OWNER_REVIEW. Reporting an independent verifier in JSON is not evidence that verification actually occurred; separately authenticated evidence is needed before promotion.

Parallel workcells: read-only source/evidence adapters; numeric residual and mask measurement; independent readback/verifier; candidate-only Blender optimizer; visual and anatomical acceptance. Exact original first-failure evidence, rights holds, producer ownership, artifact custody and release gates remain unchanged. Use standard $0 public Actions for public synthetic tasks. This is a plan/interface document until a code workcell and CI are verified; do not claim actual automated sculpting.
