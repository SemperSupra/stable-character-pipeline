# Visual QA #150 — Local OpenCode actor AOR, sync and evidence contract (v1)

**Target model:** Qwen3-Coder 30B A3B Q6_K through OpenCode on the user's Mac.
**Mission command:** actor chooses implementation details and executes within its assigned bounds, but reports short independently verifiable results after each bounded unit; owner retains promotion and other-case tasking authority.
**Authoritative owner:** [Visual QA DLE issue #150](https://github.com/SemperSupra/stable-character-pipeline/issues/150). This file and associated draft PR are an **AOR proposal**, not a replacement for DLE authority.

## Fixed workset and acceptance

| Field | Value |
|---|---|
| Repository | `SemperSupra/stable-character-pipeline` (NOT the separate `stable-character-pipeline-private` R009 prototype) |
| Case exclusively owned | `male_jump_slippers`, its 40-frame original rights-only joint source, animated GLB, 20fps H.264 |
| Baseline PR | [Ninefix #424](https://github.com/SemperSupra/stable-character-pipeline/pull/424) **draft**, branch `qualification/visualqa-nine-fix-original-corpus-r1-20261112` |
| Pinned ninefix baseline | `d470ab9566d479bf3ca3b53cf63be5ea75217b57` (on a different head -> STOP and report, do not silently rebase) |
| Baseline source result | 19 PASS / 2 FAIL / 1 UNKNOWN; two source failures slipper-jump and cartwheel |
| Slipper-jump negative control | 26 unreachable 3D hip/ankle observations plus separately recorded stance/contact findings; the original must remain unchanged and demonstrably fail |
| Handoff | One draft PR on a dedicated actor branch, exact head SHA, before/after **real animated** GLB + H.264 and source GT, independent unmodified oracle, 22-case per-file SHA receipt, public/free disposable CI run, DLE comment |
| Promotion | HOLD until owner reviews; an isolated targeted PASS is not human realism acceptance |

## Allowed decisions and actions

Within this AOR the actor may choose and implement kinematic geometry/IK, isolated motion candidate/negative-control tests, candidate rendering and codec tests, documentation, and disposable runner setup. It may create, push and update **only its own dedicated branch and draft PR**, comment on #150, and revise its own scoped files after test evidence. Existing local changes take precedence over these generic instructions.

Preferred file isolation: `qualification/visualqa_slipper/**` and `.github/workflows/visualqa-slipper-*.yml`. A minimal change in the shared original generator `qualification/expanded_motion_corpus/build_motion_batches.py` is allowed **only when there is no clean isolated alternative**, and only with 21 non-target case GT/GLB/H264 SHA identity proved. Maintain the original source/candidate separation.

The actor may not edit the source evaluator, its thresholds, original manifests/media/negative controls, other 21 cases, PR #424's branch, other actors' branches, the default branch, private identities or rights-protected content. No forced pushes, merge, release, permanent installation/cache on a persistent host, paid/private Actions or production claims. If necessary to violate a boundary, record a blocked DLE item and stop before the boundary.

## Reconciliation: distinguish LOCAL HEAD from remote authority

The actor must run a **read-only inventory BEFORE any branch switch/pull/edit**. In the existing checkout, print:

```sh
git remote -v
git status --porcelain=v1 --untracked-files=all
git branch --show-current
git rev-parse HEAD
git log -4 --oneline --decorate
```

Confirm that `origin` is an **SSH** remote to the public repo (e.g. `git@github.com:SemperSupra/stable-character-pipeline.git`). Then fetch without merging or changing any working files:

```sh
git fetch origin --no-tags
git rev-parse origin/qualification/visualqa-nine-fix-original-corpus-r1-20261112
git merge-base HEAD origin/qualification/visualqa-nine-fix-original-corpus-r1-20261112
git log --oneline --left-right --cherry-pick HEAD...origin/qualification/visualqa-nine-fix-original-corpus-r1-20261112
```

If fetched baseline is NOT the exact pinned SHA, **stop and report drift**; no assumed successful synchronization. If the working tree is dirty, detached, local commits are unpushed, branches diverge, or a candidate branch exists remotely, do **not** automatically `checkout`, `pull`, `reset`, `rebase`, `stash`, `clean`, `push --force`, overwrite branch history, or delete old work. Instead, preserve the work, enumerate the state and identify a non-destructive safe continuation on the *same owned branch*. Document anything requiring owner arbitration, but independently continue unrelated safe checks.

If the workspace is clean and there is **no existing local actor branch/work to preserve**, create a dedicated branch from the pinned baseline:

```sh
git switch -c workcell/visualqa-male-jump-slippers-r1-20261112 origin/qualification/visualqa-nine-fix-original-corpus-r1-20261112
```

Never create an empty replacement branch if there is already local progress. When ready to publish, use SSH `git push -u origin HEAD` **without force** and open **one draft PR** with base `qualification/visualqa-nine-fix-original-corpus-r1-20261112`. If `gh` exists, use its authenticated CLI; otherwise use GitHub web for PR publication, or leave the push SHA and explicit publication blocker in the DLE. No unsupported claim that private Mac work is visible remotely.

### Five small bounded work packets; do NOT collapse them

**WP0 — Discover and report authority (first invocation).** Read this contract and DLE #150, then run the read-only inventory and fetch above. Output one compact baton: repo, branch, local HEAD, fetched baseline SHA, working-tree cleanliness, local-only commits, candidate file paths, divergence, and exactly one next safe action. Post it to DLE when credentials support it. If no DLE write path exists, publish the same baton in the dedicated draft PR or return copy-ready text; clearly mark *not published*. **No motion code in WP0.**

**WP1 — Reproduce the failing slipper-jump case (second invocation).** With the baseline, SHA-verify original source labels, actual animated GLB and 40-frame/20fps H.264; use the *unchanged* independent source oracle to reproduce the **26 unreachable leg endpoints** and separately count original stance defects. Produce a small machine JSON + human summary and make the negative-control tests fail closed on missing data, wrong hash or wrong target. Commit/test/push only WP1 scoped files; add DLE/PR receipt. Do not repair yet.

**WP2 — Candidate motion geometry (third invocation).** Implement exactly one isolated coherent proposal for reachable hip-knee-ankle trajectories and true grounded/airborne constraints; derive labels from actual support mechanics rather than posthoc changing labels to pass an evaluator. Hold original tests and media unchanged. Run original FAIL vs candidate targeted source audit, negative controls, and 21 non-target SHA preservation. Produce one commit and machine-reported before/after values. STOP on unexpected collateral changes.

**WP3 — Real media/independent cloud proof (fourth invocation).** Generate actual 40-frame animated candidate GLB, 20fps H.264 and GT from WP2 with source SHA receipts. Run real codec/pixel and separate independent 3D/source negative-control judges in disposable free public Ubuntu GitHub Actions (pin actions; no paid/private runs). Demonstrate 21 other cases are byte-identical. Report exact-head run URL and terminal outcome—**never call queued/running jobs successful**.

**WP4 — DLE and handoff (fifth invocation).** Confirm that published draft PR head SHA, source/GLB/H.264 artifacts, actual CI results and #150 comment all refer to the same committed candidate. Preserve the evidence in owner-private Drive with upload/readback hashes if connected; otherwise mark durable media custody open. Record residual FAIL/UNKNOWN, limitations and next action. Stop; owner authorizes cartwheel work only after this handoff.

## Per-work-packet DLE baton

```text
Actor: OpenCode / Qwen3-Coder 30B A3B Q6_K
AOR: male_jump_slippers | WP#: 0..4 | status: PASS / FAIL / BLOCKED
Repo: SemperSupra/stable-character-pipeline
Local branch and HEAD: ...
Pinned/fetched ninefix base SHA: ...
Local dirty/unpublished work: ...
Owned files changed (if any): ...
Original negative control SHA + findings: ...
Candidate GT/animated GLB/H264 hashes (when produced): ...
Independent test command + terminal result: ...
Draft PR / GitHub Actions run link and exact HEAD (if published): ...
Other 21 cases unchanged? YES / NO / NOT_TESTED
Next bounded action: one sentence
Limitations / blocked owner decision: ...
```

Publication assertions must be literal: a DLE comment or PR is **published only when its link is verified remotely**. An unpushed local commit is not a published handoff. If GitHub is unavailable, preserve local progress and return a copyable handoff; do not claim success or repeatedly retry uncontrolled network operations.
