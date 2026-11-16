# R036 independent BodyParts3D 4.0 semantic coverage audit

This workcell **does not import the 136MB/62MB 3D mesh archives**. Its first task is an admitted, version-identified inventory of the official **FMA concept to BP representation** mapping from BOTH IS-A and PART-OF ontologies, plus their distinct parent/child relations, source SHA, source crosswalk differences and named concept candidates. The two graphs must not be merged as though IS-A means containment or each FMA concept is a distinct render mesh.

Official live sources (LSDB Archive BodyParts3D 4.0; publicly CC BY 4.0 at the time of the audit, but license/version should be recorded per archive):
- https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/isa_parts_list_e.txt
- https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/partof_parts_list_e.txt
- https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/isa_inclusion_relation_list.txt
- https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/partof_inclusion_relation_list.txt
- https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html

**Risk:** "LATEST" is mutable. The first actual run captures full SHA256 for the 4 source text files and records source-row/parent findings. A later commit must pin all observed SHA256, with fail-closed drift checks on *every* run. This README describes a metadata source candidate, not complete modeled anatomy or commercial distribution clearance for every derivative.

Controls: enforce TSV schema, valid FMA/BP IDs, conflicting duplicate mapping rejection, empty/invalid input, cycle detection, per-relation parent nodes without corresponding source mapping tracked as UNKNOWN not fabricated mesh availability. Report exact source code SHA+Go version/CPU in GHA; use disposable standard public GHA runner 5 min, Go stdlib, offline tests/race/vet. No LLM, no private model, no asset binaries, no publication/merge/release.

**Next:** use the source graph to make phenotype/system × named-structure coverage categories (`GEOMETRY_CONFIRMED`, `REFERENCE_ONLY`, `MISSING`, `UNKNOWN`), crosswalk recognized IDs with HRA/UBERON and make a source rights matrix before selectively trying the heavier OBJ archives. A named concept alone is NOT source mesh proof.
