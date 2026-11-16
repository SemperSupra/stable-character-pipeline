# R062 — public GitHub Actions local-model agent qualification

**Authority:** [private R009 DLE #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23); [private batch-first candidate #177](https://github.com/SemperSupra/stable-character-pipeline-private/pull/177); [public R060 #602](https://github.com/SemperSupra/stable-character-pipeline/pull/602); [public R061 #605](https://github.com/SemperSupra/stable-character-pipeline/pull/605); [canonical Way of Working v0.0.4](https://github.com/SemperSupra/engineering-governance-private/blob/main/WAY_OF_WORKING.md). This is a disposable research workcell, not a new DLE, scheduler, or authority.

## Bounded mission

Determine whether an existing **Qwen Code** headless agent, served by an **Ollama CPU-local Qwen2.5-Coder 1.5B** model inside standard **public** GitHub Actions, can add useful, independent source-only Go regression tests with zero paid inference, without any private input, credentials, host access, or model API key.

The [workflow](../../.github/workflows/r062-free-local-agent.yml) runs two independent matrix workcells concurrently, each on its own clean Ubuntu 24.04 checkout. The **path-boundaries** lane may only add `research/r051-batch/r062_paths_test.go`; the **strict-json** lane may only add `research/r051-batch/r062_json_test.go`. It uses Qwen Code headless `auto-edit` rather than `yolo`; no auto-approval for shell operations. Workflow token is read-only and checkout does not persist credentials.

## Reproduce / inspect

1. Observe PR-triggered GHA jobs; never assume a workflow dispatched or completed merely because this YAML exists.
2. In each job, inspect Ollama model digest, Qwen Code version, prompt, actual agent exit, `git status`, candidate diff, `go test -race`, `go vet`, and JSON receipt.
3. Download the three-day public-safe job artifact; `PASS_NARROW` means **generated diff limited to owned file and source-only Go tests passed**. No claimed native Blender, third-party source, protected identity asset, human-quality, issuer, product, release, or model-comparative acceptance.
4. A nonzero model exit, empty diff, unauthorized modification, test failure, provider failure, or exhausted runner budget is `FAIL` / `UNKNOWN`, with evidence. Do not hide REDs. The source PR is draft and cannot auto-merge.
5. Reconcile exact PR head, workflow run/job identifiers, first failure, verified tests, and next bounded action to existing R009 DLE #23. Never upload private manifests/receipts or identity media to this public runner.

## Operational boundary

No secrets are passed to the model. The model server listens only on the runner loopback interface; all jobs are disposable. The model and npm package are initially version-discovered and must be pinned by digest/version after the first compatibility bake-off before repeatable qualification. The Ollama container is explicitly version-tagged `0.13.2`; the Qwen Code package is intentionally first-probed at `latest` to discover whether it and the runner Node runtime interoperate, not to establish reproducibility. No new scheduled workflow, no private GHA minutes, no paid API, no writeback into the authoritative owner branches.

**Status at authorship:** NOT_RUN. Only provider-observed GHA results can advance it.
