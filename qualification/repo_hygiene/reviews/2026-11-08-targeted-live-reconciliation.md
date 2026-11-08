# 2026-11-08 read-only GitHub crosscheck — eight parent-SHA drifts

Authority: [R009 public DLE #272](https://github.com/SemperSupra/stable-character-pipeline/issues/272), existing [read-only hygiene workcell #312](https://github.com/SemperSupra/stable-character-pipeline/pull/312). This is a dated independent observation, not a new controller, mutation policy, owner grant, CI qualification or merge decision. All referenced PRs remain OPEN/DRAFT/UNMERGED at observation.

## Inventory boundary

Creation-date-partitioned connector searches found **265 unique public OPEN PR URLs** in six disjoint windows: before Oct 26 (1), Oct 26-27 (43), Oct 28-29 (45), Oct 30-31 (98), Nov 1-4 (28), Nov 5 onward (50). Each segment returned fewer than 100 results; no overlapping URLs. This search check is NOT an independently executed full REST pagination snapshot. Last complete public #312 GHA artifact, 2026-11-07 at source `0a7e26ca26ed36edde930f0fc151044966d84838`, reported **263 open, 36 roots, 227 descendants and eight drifts**. Do not propagate those historical root/descendant counts as fresh 265-count composition. No private repository was queried by the public auditor.

## Current exact-head parent-to-child compare

Counts below are **child ahead / behind current parent** from GitHub compare. Full 40-character SHAs are included to prohibit accidental branch-name/review equivalence:

| Child / parent | Parent head | Child head | Ahead/behind | Current disposition |
| --- | --- | --- | --- | --- |
| [#95](https://github.com/SemperSupra/stable-character-pipeline/pull/95) / #90 | `98776b16021bf447822794d74684942e451bf15a` | `1967886686d008f8db33e5c90328928d5fe944ed` | 7 / 2 | DISJOINT_PATHS_REVIEW_ONLY |
| [#117](https://github.com/SemperSupra/stable-character-pipeline/pull/117) / #116 | `c650eab0f2cb8696aedf52500744a353b86a7b1a` | `6ec5e6a4286607c9c9ce2da8aa7df35a37f6ceb4` | 5 / 1 | DISJOINT_PATHS_REVIEW_ONLY |
| [#119](https://github.com/SemperSupra/stable-character-pipeline/pull/119) / #118 | `7a821e97418e2cdce8bc6ea95db1ae0ca9cb8f67` | `e54505f584e419ee3eec8b5b1a94e8e3cc274c22` | 3 / 7 | DISJOINT_PATHS_REVIEW_ONLY |
| [#332](https://github.com/SemperSupra/stable-character-pipeline/pull/332) / #325 | `8f07eca9ebc20e50543b1559f7a0da6a7a40341a` | `6165a21bea3a93201da057def377cc14f5fc4283` | 9 / 2 | DISJOINT_PATHS_REVIEW_ONLY |
| [#212](https://github.com/SemperSupra/stable-character-pipeline/pull/212) / #211 | `216cd3257512a5f0585817aa02cb55a51c80245a` | `05601ca78edd94ccef505cc3ee553078af4629da` | 8 / 2 | SHARED_PATHS_BYTE_EQUAL_REVIEW |
| [#318](https://github.com/SemperSupra/stable-character-pipeline/pull/318) / #316 | `2a4350147085e1530fc7bce328a60143fe666d9b` | `93ea16dbf9222c425ce2c5acae29e842777a9d8d` | 12 / 2 | SHARED_PATHS_BYTE_EQUAL_REVIEW |
| [#13](https://github.com/SemperSupra/stable-character-pipeline/pull/13) / #4 | `6e894c30dac98c0398339f39419a482508b1b041` | `c8ed17529cf6bbba74cd954734b45a1bb5d31bad` | 29 / 4 | UNEQUAL_WORKFLOW_OWNER_HOLD |
| [#336](https://github.com/SemperSupra/stable-character-pipeline/pull/336) / #308 | `bca50fe99ba7d84e1153cda5fbdb173d7631ce4a` | `f4ee5af5e7adf4a055e0f30d1ab64cd3c8808ec6` | 58 / 2 | UNEQUAL_WORKFLOW_OWNER_HOLD |

The four DISJOINT cases were independently checked using both PRs' complete changed-filename lists; intersections are empty. Their exact child-head public Actions are terminal SUCCESS: #95 40894206978; #117 40949501645; #119 40951068343 and 40951068627; #332 42236462124. This is successful **scope-specific CI**, not proof of exact-parent integration, rights, product quality or owner approval.

For #212/#211 the two shared `releaseproof/releaseproof.go` and `releaseproof/releaseproof_test.go` blobs match *exactly* at current refs (`fc21362ab135ae5f1951b2ac3f48ef73562781d5`, `f0b796839646280487b3a3630a24f804370c73e5`). For #318/#316 shared `.github/workflows/shetland-equine-sculpt.yml` and `qualification/shetland_pony/verify_fur_glb.py` match (`a909ee07452e40aeddcb3ef454eeff040d300f91`, `53d92cc54088c17fc9d4e3c7d44a812bb22fa5e2`). These observations narrow byte conflicts only; ancestry and owner/CI gates remain held.

For #13/#4 `.github/workflows/tropical-blender.yml` differs (parent `906d807313420b6cf80ada5e335845c3fccf4057`, child `30c7928392cf11c1907cb330d0620b9ba8139096`). Child substitutes helper tests and `install_blender_apt.sh render`/mirror path for parent's direct apt/install and loader test; installation/loader coverage equivalence NOT PROVEN.

For #336/#308 `.github/workflows/r009-parametric-native-blender-v1.yml` differs (parent `528de5eaeeecf75c5b90659363440a3c36a4a57a`, child `03222567d6bdd88c1c7f061a36eb4bb4be28f6d8`). Parent inline gate checks `scp.r009.original_bvh_surface_contact.v2`, 72 evaluated poses; child checks v1, 12. At child exact head, separate public run 42383031585 has a successful combined-native-v2 job exercising 72 poses, and other relevant source/native workflows 42383031618/42383031641 also SUCCESS. Never silently discard either the parent v2 inline gate or child's separate v2 trial without owner-controlled coverage parity and source-replay review.

## CI fanout and no-claim rule

Public [#347](https://github.com/SemperSupra/stable-character-pipeline/pull/347) head `983c59e5c1dc543815da0d3301917700979c0917` triggered inherited run 42412224636, terminal SUCCESS, job `generate-validate-render`. Its steps are original source negative controls, Blender+FFmpeg install, native original 72f two-camera render, decoded-pixel occlusion and artifact upload. **It does not run the newly generated utility apron exporter, native deformed-apron import, 72f apron-body collision, volume containment or cloth QA.** Fanout efficiency review is READY; removing this run without independent coverage comparison is NOT authorized.

## RED/BLUE disposition and next baton

- RED: Green checks + disjoint paths + byte-identical shared blobs do not prove safe rebase, merge, auto-close or release. The two unequal workflow paths are demonstrated lost-coverage risks.
- BLUE: Source owners should independently replay approved no-loss integration on disposable sources for the four disjoint pairs, then both byte-equal pairs; preserve exact parent requirements, signed/original first RED, separate scientific/contact tests and rights checks. Verify per-workflow coverage before any CI de-duplication.
- Recorder actions: one additive dated review document on **existing #312**, no application source/parent changes, no new workflow or independent PR, no branch deletions, no default-main changes, no merge/close/rebase/release/deployment/CPE. Historical #312 first failures unchanged. Existing public DLE #272 owns the next baton; protected private R009 remains under separate private authority.
