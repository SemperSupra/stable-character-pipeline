# N03D-BC — Real OpenSim recorded walking ground-force and joint-kinematic 60Hz reference

OpenSim is not Blender MakeHuman or exact 100STYLE walking trial. Its measured force channels and kinematics apply to its OWN walk only, never automatically to unrelated mocap. Upstream opensim-org/opensim-core example3DWalking exact f67ee67fa4b9de89ff8bb9466f131e52acd8b0b6; pinned ORIGINAL Git blob SHAs for subject_walk_scaled.osim, grf_walk.mot and coordinates.sto.

Two original data streams: GRF 4778 x19 at .5ms and coordinates 1350 rows at 1ms. Analyze 60Hz grid strictly within overlapping time, vertical GRF force threshold sensitivity 20/50/100N, left/right stance, double support, no support, onset counts and joint ranges. No 100STYLE/MPFB force labels without matched trial/contact anatomy. Model muscle dynamics solver NOT executed here.

**Preserved source inconsistency:** original coordinates.sto declares nColumns=40, while real data header and numerical rows contain 32. Original grf_walk.mot declares and contains 19. This does not alone invalidate motion model; it is a SOURCE_METADATA_HOLD and must not be silently normalized. Ground-force statistical witness may still be computed with exact observed row widths, with explicit source mismatch flag.

Execute 2 independent standard free-tier public GHA Ubuntu jobs: source hostile numerical tests, and real original exact pinned Git blob download/stdio source readback/independent critic. JSON-only aggregate evidence, original files ephemeral, 3d retention. No private/protected source, paid GPU/TPU, private minutes, merges or release. Governs gait DLE #662 numeric #650 private MVP #23; physical actor gait HOLD.
