# Agent reconstruction — candidate-only contract v0

Owner scope: public-original synthetic equine #293 and human #272. Protected real-person R009 private #23 stays separate.

This **Go stdlib-only contract** validates actor-proposed hypothesis, exact frozen baseline SHA256, admitted evidence SHA256, allowlisted operation, region, subject class and bounded resource budget (max 3 candidates / 300 seconds / 2048 MiB). It does not yet represent numerical parameter bounds or execute a parameter sweep. That is a required next schema addition before connecting an optimizer.

Commands from `qualification/agent_reconstruction`: `go run . capabilities`; `go run . validate proposal.json`; `go run . evaluate proposal.json report.json`. Output JSON is consistent across human inspection, CLI automation and agent consumption. There is not yet a graphical human UI or a running agent actor.

Allowed declared operations: `shape.fit`, `rig.optimize`, `motion.fit`, `render.compare`. NO operation is executed. Malformed inputs, duplicate or unknown JSON keys, private subject classes, unsupported operations, oversized budget, nonmatching baseline/evidence hashes, duplicate evidence, stale candidate, and self-reported results fail closed. Reports only **declare** an independent producer; this declaration is not authenticated. `PROVISIONAL_FOR_OWNER_REVIEW` is **not** scientific, anatomical, source-rights, release or identity acceptance. Failed/uncertain verdicts remain failures/unknowns; no model mutation or promotion is possible.

Independent batches to add after exact-source acceptance: (A) read-only input adapters for 26-joint synthetic pony and 35-joint synthetic human, (B) actual held-out multiview render residuals, (C) independently authenticated evaluator and evidence byte hashes, (D) bounded parameter vectors and candidate-only Blender execution, (E) animal/human anatomy and visual review. One writer per workcell. No protected media, credentials, network downloads, local infrastructure disclosure, private CI minutes, merge/release/deploy/CPE promotion.

Storage: source/tests/contracts in Git; run outcomes and batons in authoritative DLE; large original render/video/model artifacts in owner-private Drive with actual whole-byte hash readback. A green Go test is contract quality only, **not proof of automated sculpting**.
