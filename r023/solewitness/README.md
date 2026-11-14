# R023: evaluated-sole minimum falsifier (independent draft)

Source-safe, original synthetic Go 1.23 standard-library witness checker. Recomputes the minimum signed height against a pinned ground plane from **supplied** per-tick left/right sole vertex lists over exactly 285 quarter-frame ticks; rejects bogus minimum indices, mismatched coordinates, missing frames, invalid geometry, duplicate vertices and nonfinite values.

**Limit:** a caller can omit real vertices from the supplied list or lie about the source mesh hash. The tool **cannot independently prove** that the list comes from Blender's evaluated post-modifier mesh, that the listed sole set is complete, or that a shoe actually made physical contact. Upstream independently witnessed extraction and source-local visual review remain mandatory. Do not upload protected geometry to public CI. Synthetic fixtures only. No CI or numeric admission grants source license, human likeness, cinematic quality, CharacterPack canonicalization or release.

Research DLE: private R014 #138, R009 #23. Independent companion to existing draft #503, not a modification or merge of that draft.
