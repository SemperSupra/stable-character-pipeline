# R009 repository hygiene workcell — permanent execution-stage gate

Scope: **public SemperSupra/stable-character-pipeline only**. A private registry has separate rights, custody, and access constraints. This is a source-original, stdlib Go implementation that performs **GET-only** pagination of open PR metadata using the ephemeral default GitHub Actions token with read-only permissions. It **does not** merge, close, delete, change refs, edit DLE, create issues, or release anything. It will not silently claim a complete inventory if pagination stops at the configured limit.

## DOPAV each batch

1. **Observe/discover** exact PR head/base SHAs, open/closed/draft, chain ancestry, first failures, CI and artifact custody.
2. **Plan** classify: eligible for independently verified cleanup, stacked-active, blocked, missing-parent, stale-review, same-head review, incomplete inventory.
3. **Apply** only separately authorized merges/closes/branch deletes once exact independent evidence proves safe. **No apply action lives in this auditor**. Do not confuse green CI, staleness or a shared source SHA with an owner-approved release/merge.
4. **Verify** re-fetch live PR/head/CI and archival records, then record the full result and next executable baton in public #272 and any owning private authority as appropriate. Keep first REDs.

Repeat the loop **before and after** each scientific/workcell batch. Do not use public Actions to enumerate private PRs.

## Runnable commands

In `qualification/repo_hygiene`:

```sh
go test -v ./...
go vet ./...
go build -trimpath -o ./scp-hygiene .
GH_TOKEN="$GH_TOKEN" ./scp-hygiene --repo SemperSupra/stable-character-pipeline \
  --as-of "$(date -u +%F)" --max-pages 20 --out ./audit-current
```

The output directory must not already exist. No non-stdlib code or third-party binary is required. Use the ephemeral public GitHub Actions runner in CI; do not install into the Windows workstation. All evidence files are JSON/Markdown for humans and automated actors, with stable hashes in the Actions artifact.

## Disposition decision rules

- **READY for review** requires verification of source-owner approval, source provenance/licensing per operation, exact parent and head SHA, green applicable tests including independent first-failure falsifiers, no outstanding security, data-custody, release, human-quality or scientific gate.
- **RETAIN** applies to active child PRs whose parent is still open/unmerged, to experimental first-RED evidence, and to all unknown or restricted source lines.
- **CLOSE as superseded** is a separate verified mutation only after proof the replacement contains all intended source/evidence and no useful unique experiment, plus authoritative DLE owner decision and updated references.
- **MERGE/FAST-FORWARD** may be proposed after a real compare, zero unsafe overlap, verified CI and all holds cleared. A successful GitHub mergeability check is insufficient. Squash only if preserving first-failure evidence, provenance and reproducibility.
- **DELETE branches** only after verified final commit is reachable, protected evidence retained, dependents resolved, source-owner approved, and exact ref leased. Never delete source trees based on age.
- **HOLD** if any confidence, custody, rights or merge decision is missing. No auto-close/auto-merge.

## Verified workset, source decisions and retained first failures

The previous 100-result GitHub search cap is **not** a complete public census.
This stdlib-only runner now paginates all public open PRs and emits a complete
root DAG, exact SHA-drift source comparison, and independent main reachability
review for **leaf root PRs only**. It refuses network failures and data truncation,
and always returns **zero mutations**.

At the 2026-11-06 independent public read-only [Actions run #42153062049](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/42153062049) snapshot:

- **250 OPEN public PRs; 36 default-branch roots; 214 stacked descendants.**
- **Six parent/head-base SHA drift holds**, source-probed with exact GitHub compare.
  Four have disjoint changed filenames; two overlap files (#212/#211 release
  proof and #318/#316 Shetland).
- **13 isolated leaf root PRs** source-compared against pinned main
  `1a6f58739c9b739ca3ac6671a67f2e0710751e6b`. **All 13 have source
  commits ahead of main**. **None is already incorporated into main**, so
  no no-loss branch closure has been justified by commit reachability alone.
- Public GitHub Actions artifact `13473951033` contains source-bounded
  `snapshot.json`, `roots.json`, `drifts.json`, `root_tips.json`, human
  Markdown summaries and direct-root SHA manifest. Public Actions artifacts
  expire; records in DLE are durable authority.

The active original-character stack remains **OPEN/DRAFT/UNMERGED**:
humanization #291, wardrobe parent #292, sibling refinement #303, parametric
#308, hygiene #312. #303's portable inactive-garment import fix passed an
independent strict original Blender A5 test at an earlier exact source
[run #42152162864](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/42152162864).
**Subsequent visual review and strict foreign-mesh verification found
additional red issues**, including startup Cube contamination and two
unexpected `Icosphere` objects after factory-empty import. Do not call the
latest #303 head native-visual accepted. More generally #308's evaluated
triangle BVH witness has positive clothing/body surface crossings in every
sampled pose; its proximity proxy never proved collision-free quality.

### Source hygiene regression controls

- The #303 workflow had a genuinely malformed duplicated/truncated job source.
  It was recovered to one canonical job definition with a strict exact-parent
  source allowlist, zero original-source changes and self-verifying checksum
  receipt. The #303 test suite now includes a static regression test
  that refuses duplicated or truncated native qualification jobs.
- Do not conflate an earlier green run with a later changed head. Always
  re-fetch and pin exact source SHAs, CI and read-back evidence.
- A **clean root ancestry or disjoint diff does not authorize** merge, close,
  delete, release, CPE, Drive promotion or rights transfer.
- Public synthetic sources and tests stay on public free-tier runners.
  Private person identities, protected Naomi/Alison media, rights and
  G5/G9 custody remain under private #23/#103 authority.

### Next executable hygiene priorities

1. For root #54 (largest 82-descendant chain in a previous audit), #253,
   #20, and #22, classify exact source overlap, owner/rights/custody,
   CI/first-RED gates and mandatory ancestors; do not bulk-close drafts.
2. Triage exact SHA drift holds, retain overlapping conflict files, and
   propose only independently evidenced fast-forwards or safe no-loss
   source adoptions for owner-authorized action.
3. Record closure **of technical defect hypotheses** only where first-failure
   falsifiers demonstrably pass; keep the owning PR open while its broader
   human/scientific/rights requirements remain unresolved.
4. Run this root-census + source-reachability gate before and after each
   independent scientific batch, then update owning DLE #272 and private
   G5/G9 handoff as appropriate. Git/DLE contains source and receipts;
   governed owner-private Drive holds original-only large binaries with
   SHA-verified whole-byte read-back.
