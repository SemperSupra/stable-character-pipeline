# R063 — model-critic interview pilot (independent public CPU)

Authority: [public visual QA #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150), [public audio proposal #521](https://github.com/SemperSupra/stable-character-pipeline/issues/521) (**proposal only, not adopted**), [private R033 model critic #168](https://github.com/SemperSupra/stable-character-pipeline-private/issues/168), [private R037 DoE #176](https://github.com/SemperSupra/stable-character-pipeline-private/issues/176), and [private R009 MVP #23](https://github.com/SemperSupra/stable-character-pipeline-private/issues/23). The current [Way of Working v0.0.4](https://github.com/SemperSupra/engineering-governance-private/blob/main/WAY_OF_WORKING.md) applies; DLE = **Durable, Legible, Executable**.

This is a disposable scientific **candidate interview**, not a deployed critic, model endorsement or new control plane. Everything executes on public `ubuntu-24.04` CPU with original synthetic fixtures and **no private character images, source video, recordings, identity weights, keys, or owner preferences**.

## Candidates / specialization

| Lane | Actual candidate | Pin | Task-relevant positive and negative controls | Strictly limited inference claim |
| --- | --- | --- | --- | --- |
| Image | `HuggingFaceTB/SmolVLM2-256M-Video-Instruct` | `4d176c0088bd75e5e9291c3c3569f3d8ebbf836b` | Distinguish source-generated red vs blue central square | Simple color observation, **not** anatomy/realism |
| Video frames | same SmolVLM2 | same pin | Detect opposite left/right motion after **actual two-frame H.264 decode** | Two decoded time samples, **not** full temporal video reliability |
| Speech audio | `openai/whisper-tiny` | `169d4a4341b33bc18d8881c4b69c2e104e1cc0af` | Transcribe local synthetic English “move the square left” and abstain on silence | ASR, **not** music/ambience/soundscape/singer or physics critic |

Declared checkpoint license according to publisher model card: Apache-2.0. Separate package, weights and training-data restrictions are not independently audited by this first pilot; no checkpoint or media redistributions. Version pinning keeps the inference source explicit. CPU Torch 2.6.0, Transformers 4.57.1, no hosted secret API.

## Recalled candidate interview / staged qualification

1. **Discover & register**: owner use case, existing alternatives, source/license/weights, model-card applicability, API and hardware capability. Missing documentation or rights => `UNKNOWN` or `HOLD`, never implied admission.
2. **Capability interview**: input modalities, language (en/de/th as relevant), frame clocks, orientation and confidence/abstention, structured outputs, reproducible version, resource/cost envelope, exact per-interface behavior. The model must answer using only observed frames/samples, not target label.
3. **Blind synthetic interview**: independent frozen positive controls, deliberate counterexamples, misleading prompts, flipped sides, freeze/skate/occlusion/negative audio and silence; independent deterministic witness above model judgment.
4. **Matched DoE**: randomized frame/view/background/lighting/motion/language interventions, balanced class prevalence, cross-model equal task/time budgets and held-out source subjects. Measure false accepts first, false rejects, localization, calibration, abstention, latency, RAM, tool failures, variance. Do not assign a confidence interval from n=2.
5. **Independent verification**: compare complete predicted receipt to ground-truth geometry/physics/decode, source SHA/weights SHA, raw media hashes and negative controls; require an unrelated verifier, not candidate self-scoring; test adversarial label leakage.
6. **Decision**: `ADOPT`/`ADAPT`/`REJECT`/`HOLD`/`UNKNOWN` for **specific task envelopes**, not globally. Scientific and anatomical invariants outrank VLM/audio preference. Owner commands govern canonical model/character/release acceptance.

## Executability and stop rules

Run `research/r063-critic-interview/interview.py --lane image|video|audio --out /tmp/source-only-evidence` in the environment provisioned by [R063 CI workflow](../../.github/workflows/r063-critic-interview.yml). The three matrix jobs are independent and have 20-minute outer caps; internal inference receives a shorter time cap. They store only three-day JSON/log artifacts, not source-derived images/videos/audio. The JSON receipt records pinned model, exact source SHA, original synthetic fixture digest, raw text, true label, oracle verdict, first failure, elapsed and explicit acceptance=false.

**No semantic PASS until actual GHA jobs finish.** Even all three `PASS_NARROW_SYNTHETIC_ONLY` outcomes mean only two tiny synthetic controls per modality. They cannot qualify actual incorrect knee anatomy, ground contact, foot skate, facial identity, photorealism, temporal coherence, hearing/voice physiology, music or creative audio. Real project media requires separately admitted sovereign execution and independently verified rights.

## MCP / Cloudflare boundary

An ephemeral Cloudflare Quick Tunnel is a possible remote HTTP transport, but it **does not install an MCP client or tool into this chat**. Quick Tunnels offer no permanent endpoint; an unauthenticated URL is public to anyone who knows it. Email one-time-code auth is interactive and unsuitable for unattended MCP calls. Do **not** expose unrestricted Ollama inference, developer shells, GitHub tokens, protected model weights, private asset roots, or write-capable execution over `trycloudflare.com`.

Prefer existing authorized GitHub connector + Actions run/artifact evidence while a custom MCP app is not actually connected. If a custom endpoint is admitted later, reuse a vetted Streamable HTTP MCP server with explicit OAuth/token, read-only `list_candidates`, `get_receipt`, and `get_status` surfaces, short TTL, provenance and abuse limits. The user must explicitly connect it in ChatGPT on the **web** using a supported plugin/app flow; capability availability and write permissions are plan/workspace dependent. Neither the mere URL nor a successful cloudflared tunnel proves ChatGPT can invoke it. No unattended tunnel or new service is created in this pilot.

## DLE handoff

At each observed result record **source PR/head, GHA run/job IDs, exact first RED, limitations, and next bounded action** in the existing #150 / private #168 / #176 DLEs as applicable. Preserve failed evidence, leave draft branches unmerged, no private Actions minutes or paid API, no automatic release or interpretation beyond measured truth.
