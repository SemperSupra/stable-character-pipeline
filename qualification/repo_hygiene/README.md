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

### 2026-11-06 live follow-on camera, rig35 and actor workcells (source-only custody)

Owner-coordinated independent public-original synthetic batches were added as three
**distinct, additive, draft/held descendants** with exact parents:

- Camera intrinsic declared-heldout observer [#332](https://github.com/SemperSupra/stable-character-pipeline/pull/332) from #325 at `672edf4842a409deb1e10d573148e292ec05351d`, child source `2f4b108da7357ae3a85708ff5ff60f80355b5c0e`; exact-head public Actions `42154699209` SUCCESS. Real photographic calibration still NOT_RUN.
- Human 35-joint temporal read-only falsifier [#333](https://github.com/SemperSupra/stable-character-pipeline/pull/333) from #326 at `188d6b05b14d517cf6f6839827ebe955a7134eb9`, child source `6c5df19ddee36d83112f187c44353ef6f9a025b4`; exact-head public Actions `42154961062` SUCCESS. Biological JCS/ROM and visible seam defects HELD.
- Exact archived native multiview actor-vs-rule challenger [#334](https://github.com/SemperSupra/stable-character-pipeline/pull/334) from #317 at `fb581c7073bb42ec912c476fd7669508a9f3789d`, child source `ec58c3d2a3778bea54c37817c5b0cc7f4dca83d1`; exact-head public Actions `42156030570` SUCCESS. Uses actual archived native synthetic image metrics but actual LLM/VLM inference NOT_RUN.

All three are distinct additive owned paths; all remain **OPEN/DRAFT/UNMERGED** and
retain rights, photographic source, native human/pony quality, release, CPE,
and merge holds. Do NOT count these as duplicate cleanup targets or "already
integrated" from a local source test. Re-run complete real public PR inventory
rather than adding three to a stale 250-count snapshot, preserve all six
historical SHA-drift pairs and source-first failures, then write owning
DLE #293/#272 verified exact-head batons. No source branch reset, PR close,
merge, deletion, private Actions, or CPE in this read-only audit update.

### 2026-11-06 continuation — test-exact motion observations, no autonomous closure

**DOPAV observed 2026-11-06:** Existing public-original synthetic owner branches #330 (Shetland) and #333 (original rig35) were advanced in disjoint workcells; **no new coordination PR, main change, protected-source access, merge, close or branch deletion**.

- #330 previous exact native integrated head `406e5f6418377fd16f6d385d6be2b52bdcdbcc12` fully **SUCCESS** ([42157879099](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/42157879099)). The archived native MP4s (side, face, mane, tail, 48 frames each) were downloaded and independently inspected; the source-original GLB/tack screen still fails **scientific appearance**. Contact-sheet evidence is local output, not photographic acceptance. Existing nearest-triangle five-pose halter screen is only a proximity diagnostic, not collision/ethology proof.
- #330 added **independent decoded video image-motion observation** and hostile unique-pixel/noise, frozen, missing frame, malformed receipt and SHA-drift controls. Unit tests **7/7 locally with actual 4 native MP4s** PASS before Git write. New head `848bfc55e3405928d9f93deb60446f2f9d84ef82` exact native [42165053677](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/42165053677) was **IN_PROGRESS** at initial observation; no future PASS assumed. Source rights/appearance/hoof/ROM/protected identity HOLD.
- #333 adds an independent **signed source-local X hip/knee/ankle authoring-limit** falsifier, observed on actual before/after synthetic GLBs from original native #308; 12 source-bounded tracks, 72 samples each, signed knee values remain within authored limits. **This is NOT anatomical human JCS or normative ROM.** Source hostile tests **6/6 locally** PASS. New head `70305c6646ef94c855e7a7b9a2ccd67bba82f455` exact native [42165327693](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/42165327693) was **IN_PROGRESS** at initial observation. Do not mistake it for older #333 CI proof.
- Handoffs and first REDs remain in public #293 and human #272. Protected private R009 #23 and G5/G9 #103 govern real identity rights, deployment/CPE and private runners. Native artifacts are ephemeral; large binaries go to owner-private Drive **only after full-byte download-back SHA verification**. New source/short receipt stays Git/DLE. Preserve historical six base-SHA-drift holds; no auto-close on old green CI or unchanged draft age.

**Next read-only census** at this exact hygiene HEAD must derive the current open-PR count and root tips, not inherit the earlier 253 result. Any cleanup candidate must have no-loss source equivalence, first-RED preservation, actual rights and owner approval, and verified post-mutation state. Keep these two new source owners pending terminal native CI before any scientific claim.

### 2026-11-06 source-owner bounded continuation, 48f tack and 72f human anchor

The independent execution lanes continue in **existing** distinct draft PRs,
not new DLE/coordination PRs, not public default branch, and not protected
Naomi/Alison custody. Parent SHAs remain unchanged.

- Shetland #330 exact source `113811744ee0a7529c41e3aac63d91dbbb47a935`
  adds an actual native 48-source-frame **evaluated head/halter mesh triangle
  BVH** and positive-crossing/negative-separated calibration; records head-world
  motion versus *head-relative shape state*, so repeating an unchanged
  tack-to-head pose for 48 frames does not count as 48 independent scientific
  tests. Its native run `42173374397` must reach terminal status and its
  receipt must be inspected before calling this new evidence qualified. Any
  triangle candidate or zero head-relative dynamics preserves tack science RED.
- Original-human #333 exact source
  `457e7f9f590f71ff2c5867b7dcde0c29434b0fe2` independently
  computes every source foot-joint world transform for two 35-joint original
  people across 72 frames. Public native [run #42173723127](https://github.com/SemperSupra/stable-character-pipeline/actions/runs/42173723127)
  SUCCESS; receipt artifact `13481529356` downloaded, CRC PASS, source SHA
  `470ec8fc159912e8ad2e30733a00c09785e11c1275c26936774690fe2807727b`.
  There are **78 candidate joint-anchor skate instances across 560 support
  interval marker tests**, not confirmed foot-sole penetration or human gait
  failures: the synthetic floor is inferred from minimum foot-joint height.
  Actual terrain, pressure, contact, clothing/body BVH and normative JCS remain
  unqualified. Preserve the misleading-green-physics falsifier for the owner.
- This #312 runner remains the **single read-only root/DAG/drift hygiene
  authority**: regenerate a fresh complete paginated census and source
  reachability, distinguish closure candidates from owner authorizations,
  and never mutate branches, PRs, approvals, release or CPE. Preserve six
  observed drift holds unless a fresh compare proves otherwise. No redundant
  new child PR and no default branch source mutation was created by these two
  engineering batches.

Store scripts, SHA evidence and DLE baton in Git; keep generated large model
and video binary in controlled owner-private Drive only after **whole-byte**
remote readback, not merely successful local extraction. Public $0 Actions
artifact retention is seven days and does not itself establish durable Drive
custody.
