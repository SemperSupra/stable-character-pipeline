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
