# Source-safe repository hygiene as a mandatory workcell

This is an **original Go 1.23 stdlib, read-only GitHub PR/DLE-adjacent observer** for the public Stable Character Pipeline. It is not a GitHub merger, stale-PR cleaner, release controller or owner substitute.

## Discover → Observe → Plan → Apply → Verify
1. **Discover:** validate explicit `scope.json`; no hidden org-wide scanning, private owner contents or third-party dependencies.
2. **Observe:** GET each PR's live head and base SHA, state/draft/merged flags, changed paths and first-page exact-HEAD Actions runs. Read-only GET requests; API error stops the audit.
3. **Plan:** reconstruct branch ancestry, flag stale base SHA versus the actual parent PR head, classify inherited path overlaps separately from **independent collisions**, and record CI as `EXACT_HEAD_WORKFLOW_SUCCESS_NOT_OWNER_ACCEPTANCE`, running/failure, or UNKNOWN.
4. **Apply:** atomically write **only a local** content-digested JSON receipt, never mutate GitHub. The same inputs create the same digest. No merge/close/delete/release operation exists in the executable.
5. **Verify:** independently read back and verify digest, deterministic ordering, PR count and policy guard fields. This confirms receipt integrity **not current remote liveness**; rerun Observe for fresh status.

Commands from `qualification/repo_hygiene`:
```
go test -race -count=1 ./...
go vet ./...
go run . -mode plan -scope scope.json
go run . -mode apply -scope scope.json -out ./hygiene-receipt.json
go run . -mode verify -out ./hygiene-receipt.json
```

The public GitHub Actions workflow runs all three modes on the same source snapshot (the local plan and remote observe may differ when concurrent actors commit), blocks confirmed sibling path collisions or stale child base heads, and uploads the JSON receipt even on a failed gate. It uses only a read-only per-job `GITHUB_TOKEN` (no token printed) and a disposable standard public Ubuntu runner.

## Three audiences
- Human: PR DAG/overlaps, first RED preserved, dispositions (CLOSED_UNMERGED_RETAIN_FIRST_FAILURES, OPEN_DRAFT_RETAIN_OWNER_GATES, etc.) and explicit cleanup questions.
- Automation: strict JSON `scp.repo_hygiene_receipt.v1`, digest, deterministic gates and statuses.
- Agent: may recommend source-owner actions from the read-only receipt; **not authorized to click merge/close/delete**.

## Not an automatic closure policy
A green CI job or GitHub `mergeable=true` is not scientific acceptance. A closed unmerged first-failure PR must retain source and evidence. An unmerged draft with rights, custody, source adoption, protected-runner, scientific UNKNOWN or owner gates must remain open. Actual closure, squashing, adoption, branch cleanup and CPE/release promotion require their own observed final authority and approval; this observer cannot grant those. GitHub checks are identified by **exact current commit**; even an exact-head success does not prove all named science assertions passed.

## Source custody and error conditions
The input scope lists **only public issue-linked workcell PRs**, not private release source or protected person/media identifiers. No private data enters public CI. The result preserves exact commit IDs and changed-file paths but no logs, private token or local sovereign infrastructure. Failure cases include API 403/rate limit, stale parent, independent changed-file collisions, or incomplete GitHub pagination. First failures remain in owning DLE; this receipt is an index, not a replacement evidence store.

## Hygiene at the end of *every* independent batch
Before declaring completion: reconcile the exact PR head and CI; list and compare changed paths; confirm single-writer source and current stacked parent; check first scientific failure and retained proof; verify source/read-only rights and binary custody; resolve duplicate work; close only truly completed superseded work with durable rationale; check branch deletion safety; record exact next baton in owning DLE. If a source update changes a head, rerun rather than claim an old green result.

Next independent improvements: annotate PRs with exact-source public checked CI and custody receipt IDs; add owner-approved closure decisions as signed evidence, expand an authorized scope through review, integrate receipt into both human and equine PR checklists. No automatic main merge, release, deploy, CPE, protected-source access, or private Actions minutes.
