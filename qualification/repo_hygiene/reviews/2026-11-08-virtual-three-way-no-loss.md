# Four-source exact Git tree virtual joins — 2026-11-08

Authority: public [R009 DLE #272](https://github.com/SemperSupra/stable-character-pipeline/issues/272), existing source-safe [housekeeping PR #312](https://github.com/SemperSupra/stable-character-pipeline/pull/312). This is a **non-mutating, exact-head file-state review** over public original-only Git trees. It does not create a Git merge tree, apply a patch, push any tested candidate to a source-owner branch, run the new candidate's native motion tests, establish rights, or approve merge/rebase/close/delete/release/CPE.

## Source triplets and independent readback

GitHub GET `/git/trees/{commitSha}?recursive=1` was executed against *all three* public commit identities for each workset. All 12 returned tree representations had `truncated=false`. The decoder compared **leaf blob/submodule Git SHA+mode+type**, not merely file names, and constructed a virtual base+parent+child file map. The parent and child changed paths were disjoint, and each final file state matched the source tip that modified it. Full resulting maps also had no case-insensitive path collision or file/directory prefix collision.

| Child / parent | Historical base | Current parent HEAD | Current child HEAD | Base/parent/child leaves | Parent/child changed | Virtual final leaves |
|---|---|---|---|---|---:|---:|
| [#95 / #90](https://github.com/SemperSupra/stable-character-pipeline/pull/95) | `29691e4213d837d29f68741318de3a3dbda2a392` | `98776b16021bf447822794d74684942e451bf15a` | `1967886686d008f8db33e5c90328928d5fe944ed` | 31 / 31 / 38 | 1 / 7 | 38 |
| [#117 / #116](https://github.com/SemperSupra/stable-character-pipeline/pull/117) | `7afc9dfb5a70736412347d2c9316d652583f8458` | `c650eab0f2cb8696aedf52500744a353b86a7b1a` | `6ec5e6a4286607c9c9ce2da8aa7df35a37f6ceb4` | 8 / 8 / 13 | 1 / 5 | 13 |
| [#119 / #118](https://github.com/SemperSupra/stable-character-pipeline/pull/119) | `da9744445e679bd611e183447db14943dd061619` | `7a821e97418e2cdce8bc6ea95db1ae0ca9cb8f67` | `e54505f584e419ee3eec8b5b1a94e8e3cc274c22` | 22 / 22 / 25 | 6 / 3 | 25 |
| [#332 / #325](https://github.com/SemperSupra/stable-character-pipeline/pull/332) | `672edf4842a409deb1e10d573148e292ec05351d` | `8f07eca9ebc20e50543b1559f7a0da6a7a40341a` | `6165a21bea3a93201da057def377cc14f5fc4283` | 6 / 7 / 10 | 2 / 4 | 11 |

**All four:** `VIRTUAL_TREE_DISJOINT_NO_LOSS_CANDIDATE_REVIEW_HOLD`; no integrated Git SHA or accepted merge request exists. Historical base tree tips and current parent/child content are *public* source only. The parent and child exact-source Git compare counts were respectively 7/2, 5/1, 3/7 and 9/2 ahead/behind.

## Reusable strict public-source primitive

The independent Go standard-library `virtual_merge_v1.go` models `VirtualTreeTriplet` with public-repo allowlist, SHA-ref checks, truncated-tree rejection, leaf SHA/mode/type integrity, complete source-path union, no overlapping edits, normalized-path and cross-platform case collision checks, file/directory ancestry collision rejection, and opt-in symlink/submodule change HOLD. It creates a **separate deterministic SHA256 fingerprint of the virtual source file-state map**, *not* a real Git tree ID or branch commit. Every successful result still emits `OwnerApproval=false`, `Mutations=0` and an unmerged reviewer disposition.

Adjacent `virtual_merge_v1_test.go` exercises deterministic source-preservation positives and hostile source controls (duplicate changed path, duplicate entry, truncated GitHub response, invalid head/repo/path/mode/SHA, symlink, submodule, case collisions, file-directory collision and no accidental promotion). This first increment is a **pure local Go verifier**, used by tests; no new GitHub network action, CLI transport, or automatic live no-loss admission is claimed. Live 12-tree inspection above was separately performed via connector reads and is *not* silently attributed to the Go test suite.

## Red/blue adjudication and baton

- RED: File-level disjointness cannot prove semantic compatibility, build/test parity under the **combined** tree, physical/biomechanical correctness, human visual quality, rights or source-owner adoption. A parent branch's later commits may be required by its child; a fast-forward/rebase can change tested source and require new CI. No blind update.
- BLUE: Exact-source mechanical no-loss is **candidate-level** on four worksets. Owner reviewers should run isolated real Git merge-tree/disposable checkout with all applicable parent/child tests and first-RED controls, compare SHA-bound runtime results, and review sources/rights before deciding whether to advance child refs.
- Independently preserve two unequal workflow holds: flora #13/#4 alters Blender installer and loader coverage; original human #336/#308 conflicts on v1/12-pose vs v2/72-pose inline BVH gate. Keep both science validators and avoid CI fanout changes until coverage parity is proven.
- Housekeeping action is additive documentation and scoped Go-source tests under existing public #312 only. No default-main, source-owner, private identity, asset, workflow, PR-close/merge, branch-delete or CPE mutation. DLE #272 retains current next baton; private owner DLE #23 gates protected R009 separately.
