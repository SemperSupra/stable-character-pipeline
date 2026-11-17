# R068 — 3B local CPU coding-agent qualification with independent mutant sensitivity

**Provenance / authority:** stacked on original [R062 draft #606](https://github.com/SemperSupra/stable-character-pipeline/pull/606) exact source head `c4aa1dbe131df86198ab943695f59f26c4f12c36`, preserving its failure evidence. Existing private R009 [DLE #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23) remains authoritative; private local actor batch [draft #177](https://github.com/SemperSupra/stable-character-pipeline-private/pull/177) remains untouched. Canonical Way of Working, DLE = Durable, Legible, Executable.

## Controlled candidate change

R062 Qwen Code 0.27.4 + Ollama Qwen2.5-Coder 1.5B failed both lanes by wall-clock 240s; bounded direct Go→Ollama adapter with same 1.5B generated invalid Go syntax in both lanes. R068 changes **only the open-weight model** to `qwen2.5-coder:3b-instruct` on a disposable CPU-local Ollama 0.13.2 instance and uses existing exactly-scoped Go one-shot prompts and parser. From the official Ollama model catalog: 3B is approximately 1.9GB Q4; the 3B weights use the **Qwen Research License**, not the Apache-2.0 license of the 1.5B candidate. Treat checkpoint as **RESEARCH-ONLY, NOT PRODUCT ADMITTED**, pending exact license/weight audit. Public source-only isolated qualification is not release authorization.

Two independent 10-minute standard-public Ubuntu CPU jobs `path-boundaries` and `strict-json` each:
- Preflight existing Go adapter and R051 source tests; pull a **local** 3B model over normal public model registry transport and record Ollama digest; no paid model API keys or external prompt exposure.
- Give the model at most 180s inference to propose one newly owned Go test file. Disallow all changes to existing source or other paths. Save the candidate diff and raw results.
- Require syntactically valid Go, offline `go test -race`, `go vet`, and an independent **falsifier**: a disposable copy of source is deliberately mutated (path overlap must always falsely return false; nested duplicate-key guard is disabled, respectively). The generated test **must fail the hostile mutant**; generic empty or inert tests must not pass merely because they compile.
- Never push model-generated code automatically, change owning branches, merge, accept, execute protected source assets, restart exhausted actor, spend private Actions minutes or claim R009 film completion.

Results must report `PASS_NARROW_SOURCE_ONLY`, `NO_CANDIDATE`, `SYNTAX_FAIL`, `TEST_FAIL`, `MUTANT_SURVIVED`, `OUT_OF_SCOPE`, `MODEL_EXIT` or `NOT_RUN`, with actual tested source SHA, exact model size/digest, first RED, host run ID and bounded artifact.

This is an *interview of model–harness interaction*, not proof of general coding-agent competence. Qualify with fresh held-out tasks, changed seeds, transfer across repos and license admission before considering any workflow adoption. No Cloudflare endpoint, external MCP admission, private repository checkout or public result publishing beyond this synthetic test.
