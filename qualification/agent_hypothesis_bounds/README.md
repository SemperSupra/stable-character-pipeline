# Candidate-only reasoning-actor parameter bounds (original synthetic pony)

This is a standalone additive workcell under public equine DLE #293 and shared agent #300. It admits a typed JSON proposal from a reasoning actor but does **not** run an LLM, execute Blender, modify canonical geometry or grant promotion rights.

Input `scp.actor_parameter_plan.v1`: experiment ID, public-original-synthetic-equine source, baseline and reference SHA256, explicit source joint `neck`, axis `Z`, numeric angle interval within [-0.75,+0.75] radians, exactly three samples, evidence class `public_original_synthetic_self_reference`, intent `candidate_only`. All JSON fields are strict; duplicate keys, unknown keys, extra values, invalid hashes, unrelated identities and unbounded actions fail closed.

Use `go run . plan proposal.json`; `go run . capabilities` describes the same read-only interface. Output `scp.actor_candidate_plan.v1` contains deterministic candidate IDs and the angle midpoint/ends, with no filesystem paths or executable source. The sample operator uses the native pony's bone-local Z rotation, not a universal anatomical axis convention. This contract is **not** a biomechanical prior.

### Next source-bound integration
The independent native Blender adapter should consume the exact three candidate angles and evaluate them against rendered masks from a frozen reference on at least two cameras. Record camera/frame metadata, actual generated candidates, held-out residuals, producer checksums and all first failures. Independently verify source-code and image bytes. Self-rendered reference does not validate external photo/video fitting, animal anatomy, or realism.

Human/automation/agent audiences share one JSON/CLI contract; a human GUI is not implemented. Source/tests in Git, evidence in DLE, large binaries in owner-private Drive after whole-byte readback. This is DRAFT only; no main merge, source adoption, private-runner use, release/deployment/CPE promotion.
