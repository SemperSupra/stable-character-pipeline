# Exact-source CI fanout regression — 2026-11-06

One purposeful, additive workcell-local change on original synthetic #331, following the fully green
native bootstrap of the eight new fail-closed proof gates at commit `3d7f9ebcdf1330a2d10ae0915f53937b72ee1c10`.

This path is inside `qualification/equine/kinematic_reach/**`, so the reachability
workcell must execute its real source tests and reachability computation again.
Its technical proof cannot be reused across a change in its own source scope.

The other seven workcells have **disjoint** owned source paths, unchanged workflow
definitions and the same unchanged pinned parent. Their historical native proof
is eligible for technical reuse only if GitHub provider readback proves native
success on the branch ancestor with complete, unexpired, digest-bearing artifacts.
Any provider failure, expired/missing artifact, source/parent SHA drift, unknown
path or gate-policy change must execute the native qualification again.

This is an intentionally narrow regression to measure native work avoided while
preserving existing PR check names and per-workcell science/rights/release holds.
A green GitHub check from reused identical technical evidence is NOT a new native
render, equine veterinary acceptance, source adoption, permission transfer,
scientific proof, CPE, default-branch merge or release permission.

Owning authority: public Shetland DLE #293; cross-lane R009 DLE #272 and
read-only hygiene PR #312. No protected model/data or sovereign endpoints.

## Second controlled branch-head change — provider readback repaired

The first synchronized trial at `f13c2e863df35f198b0224b13a486d6cf2340cb7`
demonstrated zero native savings because the initial workflow-file-index provider
lookup missed prior branch-native evidence. Do not call that rollout qualified.

The corrected read-only selector at exact parent `b9ebb37211ebd03eeb9aedfdf168d10d015bcca8`
queries repository-wide public Actions history, binds exact workflow path, prior
PR and base refs, ancestor SHA, completed native-job success and unexpired
provider-reported artifact digest. Its new source-native baseline has all eight
workflows completed successfully.

This additive change deliberately touches only this reachability-owned source
directory. Its own 48-frame preflight must rerun natively; the other seven
workflows may elide native steps only if the above provider proof is verified.
The result must be measured from **actual job step conclusions/logs**, not
inferred from green check status. Any uncertainty means rerun rather than waive.
Scientific animal anatomy, force-bearing hoof contact, visual acceptance, rights,
merge, release and CPE remain held.
