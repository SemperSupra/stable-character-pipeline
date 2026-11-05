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

## Known current workset / safe next steps

As of 2026-11-06 live readback: public original #291 HEAD `ce0a2743ec5d8c10fd683245cc898d33bb759025`; wardrobe #292 HEAD `31d09f2ab079880707a2e2e736af333e5c50e68d`; sibling wardrobe corrective #303 HEAD `0262cdca60a3d2351ec8ec6df915f661d888b740` A5 import FAIL; parametric morphology #308 HEAD `d5c56859ea05d80954205713f79212a8e31e5a7e` source-only tests PASS. All four remain **OPEN/DRAFT/UNMERGED**. Parent #292 is still required, and #303/#308 are sibling experimental branches. A full PR-source dependency DAG, additional mergeable candidates, stale active workset and all-lane private reconciliations require separate evidence before any closure.

The GitHub search connector capped a public PR search at 100 results; that observation is **partial**, not a full live census. The new live REST paginator must demonstrate completion before the entire repository is considered inventoried.

Protected real-person assets stay out of public source and evidence. Continue original synthetic work with $0 public runners and record Git/DLE receipts; large deliverables in governed Drive after whole-byte hash readback.
