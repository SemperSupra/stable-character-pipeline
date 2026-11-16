# R036 GLB differential qualification (independent stacked workcell)

Based on exact public parent PR #525 head `e75bd3b025841cb5aca845cb20278b68a476392a`. This workcell owns only a new reimport/geometry-measurement script and its own workflow, never modifies the parent rig probe or private R009 assets.

Build the official MPFB character with the pinned upstream addon and produce both GLBs in a disposable public Ubuntu Blender CPU runner. In a **fresh Blender process**, reload the native .blend and import each actual GLB independently, find the imported skinned body, evaluate frames 1/12/24, compare symmetric nearest-point geometry between native and importer mesh, report p95/max displacement in meters and mesh/armature inventory. A shifted-geometry negative control must be detected. The GLB may split vertices at UV/hard-normal boundaries; therefore do *not* compare by vertex index. Geometric nearest-neighbor only bounds positions, not skin semantics, bone consistency or visually accurate deformation.

**Admission:** source/asset rights already pinned in parent workcell; only original synthetic anatomy proxies, never protected identities. `MEASURED` does not mean any export accepted. No artifacts uploaded to public CI, no owner merge/release/deploy. Report exact first failure and conservatively hold target engine compatibility, material/skin/semantic parity, animations and independent visual-quality assessment.

Inputs are existing parent script output paths under ephemeral `$RUNNER_TEMP`. Dependencies installed into ephemeral runner VM, with no developer/workstation taint. Audience interface is readable JSON line for automation/agent and a human-readable readme; actual accessible human viewer remains separately unqualified.
