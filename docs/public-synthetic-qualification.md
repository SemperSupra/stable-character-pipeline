# Public $0 rig qualification — synthetic only

**Status:** experimental draft conformance harness, not released runtime, model, dataset, character-identity evaluation, or accepted R009 park animation.

Human interface: GitHub Actions checks display test names and failures. Automation: run \`GOPROXY=off go test -race -v ./...\` and \`go vet ./...\` in the conformance folder; JSON test events are available with \`go test -json ./...\`. Agents consume those same bounded exit codes and errors. These are three presentations of the same checks, not three independent implementations.

Synthetic checks:
- skeletal DAG parent ordering, bone naming, influence indices, finite weights and normalization;
- left/right limb mapping, twist exclusion, missing and ambiguous bone refusal;
- two-link analytic IK lengths, unreachable targets and nonfinite input;
- ground-contact displacement including a deliberately sliding negative fixture.

Hard boundaries: **Private Actions: 0 runs and 0 minutes**. All GH Actions qualification runs only in paired public repository SemperSupra/stable-character-pipeline. No secrets, user-provided real images/meshes, Naomi/Alison binaries, proprietary textures, passwords, private source mirroring, networked model downloads, or GPU. Workflow uses public hosted CPU with a fixed timeout, read-only permissions, cancel-in-progress and no Go module network.

This code is freshly authored as an independent synthetic reference; it is not the private Blender implementation or a private repository source copy. Its approval to enter a draft PR does **not** authorize merging to main, a source license grant, a production release, or the publication of real vendor/person source assets. Keep public release gate #1 open.

A passing public check proves ONLY synthetic invariant behavior. It does not test private R009's actual source or Blender code, natural gait, textures, vendor EULA, final two-subject scene, accessibility, or real-person likeness. Separate admitted private workcells should run the same reference tests/contract against private implementations and report only redacted receipts to the owning DLE.
