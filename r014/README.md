# R014 MHR CPU inference — independent experimental batch
This is **not** a photoreal human production model. The code runs the pinned Meta MHR `v1.0.1` TorchScript in a disposable public Ubuntu CPU runner and only emits machine receipts. The model archive is matched to upstream published SHA256, and the embedded asset LICENSE text is inspected before inference. It has 45 identity, 204 pose, 72 facial expression inputs; this short batch probes neutral and perturbed inputs, numerical finiteness, functional response and repeatability.

**Important:** TorchScript vertex positions without complete face topology/rig semantics cannot substitute for a riggable character asset; no weights, identity references, or real-person data are uploaded. Not an MPFB human comparison yet.
Native right/time/quality adjudication stays in private R014 #138. Draft/no merge.
