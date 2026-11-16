# R063 — public, bounded free-model typed-fixture qualification

**DLE authority:** [private R009 #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23), original actor handoff [private draft #177](https://github.com/SemperSupra/stable-character-pipeline-private/pull/177), product [#2](https://github.com/SemperSupra/stable-character-pipeline-private/issues/2), [Way of Working v0.0.4](https://github.com/SemperSupra/engineering-governance-private/blob/main/WAY_OF_WORKING.md). This is an independent public-original research workcell, not a new authority or canonical implementation.

## Why this experiment

Previous [R062 draft #606](https://github.com/SemperSupra/stable-character-pipeline/pull/606) was a measured RED: Qwen Code 0.27.4 + locally hosted Qwen2.5 Coder 1.5B timed out after 240 seconds on two public CPU jobs; a later direct model-to-Go attempt generated syntactically invalid Go in both tasks, rejected before writing candidate source. These failures do not prove all free models incapable, only that their corresponding harness/task envelope did not pass.

R063 keeps the real model but reduces its responsibility: **propose typed adversarial test inputs and predicted acceptance**, not arbitrarily authored source. An independently tested Go 1.24 stdlib renderer turns validated `cases[]` into syntactically formatted Go test files. The tests invoke the actual R051 `cleanPath` or R061 `decodeLocalBounded` implementation; the model's predicted PASS/REJECT is *never* treated as an oracle without running actual Go tests.

## Independent four-workcell DOE

The [workflow](../../.github/workflows/r063-free-model-fixtures.yml) schedules two local Ollama models × two workcell tasks (max parallel four) on standard **public** GitHub Ubuntu24.04 runners:

- Qwen2.5-Coder **1.5B**, relative path sanitizer; Qwen2.5-Coder **1.5B**, strict JSON admission.
- Qwen2.5-Coder **3B**, relative path sanitizer; Qwen2.5-Coder **3B**, strict JSON admission.

Each job runs its own read-only checkout; immutable model-tagged filename `r063_{m15|m3}_{path|json}_test.go` is exclusively owned. A limited-context loopback Ollama call proposes only 3–5 unique public synthetic inputs with at least two rejection cases and one acceptance case. Inputs are bounded to 320 bytes each, no NUL. No private media, repo write credential or paid inference. All generated Go source comes from a deterministic `go/format` template, not a model-authored command, code body or import. A matched baseline and adversarial generator unit tests run before inference. Post-inference job checks exact sole changed path, contentful diff, real `go test -race` and `go vet` on the existing R051 code. Expected error classifications are independently evaluated at runtime against the real implementation; a wrong model prediction produces RED.

**Single-task caps:** each public job ≤9 min; local model call ≤180s, max 320 prediction tokens; three-day public-safe evidence retention. Empty/malformed proposal, invalid admission, model timeout, model false expectation, code/test failure, source boundary breach or absent runner gives **FAIL/UNKNOWN**—not completion. No automated CI mutation, merge, release or owner-promotion.

## Three audiences and O&M

Humans use PR/durable DLE/workflow and Go test logs; automation uses `go test`, `go vet`, deterministic generator and JSON receipt; agents consume the same typed CLI admission, model selection, bounded failures, and evidence artifacts. All must observe the same status. Baseline operation requires no private API keys and no sovereign hardware. One run provides *sample-level evidence only* (no population-level quality estimate). Repeat seeds/model digest pins, more complex regression cases and additional environments require new independent qualification, not implicit acceptance.

**At creation:** NOT_RUN, until GitHub provides actual run IDs and successful independent test receipts. Preserve prior R062 RED and keep all R009 native/identity/rights/a11y/issuer/MVP release gates HOLD. Report exact run/job SHA and first RED to existing private #23; no new competing DLE.
