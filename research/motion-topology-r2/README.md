# R2 source-safe cross-topology motion falsifier

Original abstract 3-link per-leg articulated skeleton, stable joint identifiers and parent DAG; immutable test fixture. The goal is not to solve real MakeHuman animation, but to test a fundamental weakness of endpoint-only motion and critic rewards: **a foot target can be satisfied exactly by multiple different 3-joint configurations** with visibly different internal knee/ankle positions. A rig-conditioned model trained on a 2-joint target cannot learn a missing degree of freedom from foot endpoints alone.

Independent Go1.23 stdlib tests: one root/acyclic stable joint IDs and laterality; exact mathematical 3-link FK and two distinct solutions with same foot position; explicit joint range policy differentiating otherwise equally scoring poses, plus unreachable/nonfinite guards. Three disjoint public Ubuntu CPU matrix reps. Original source only; no actual MPFB/MHR, human anatomy/skin, MMD motion, true physics/contact, neural checkpoint, actual VLM, third-party data, private or paid runners, GPU or protected scene.

This is a **non-identifiability falsifier**, not a source-frame-full-body physical retargeter. It supports motion #29, MMD #19, Visual QA #150, and protected R014 #138/R009 #23/R033 #168 without replacing their owner DLEs. Longer-term target: source-conditioned anatomical landmarks + contact + chosen joint-style constraints and learned model embeddings, with multiple solutions/uncertainty when evidence is insufficient.

Run: `go test -count=1 -v ./...` and `go vet ./...`; failure nonzero. Only original source and bounded output, no binaries/artifacts or acceptance promotion. Draft/hold, three-audience README/CLI/logs. DLE = Durable, Legible, Executable.
