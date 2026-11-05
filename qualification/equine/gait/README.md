# Equine gait/contact phase experiment

DLE: https://github.com/SemperSupra/stable-character-pipeline/issues/293

Go stdlib source-only **independent** candidate; no source imports from PR #294, no third-party input media. Plans events for an idle, walk (four beats), trot (diagonal two beats), left/right canter (three beats), and left/right gallop (four beats). Fractional phase is expressed on an integral 96-tick cycle, with sample positions exact at 48 kHz / 24 fps.

**Critical limit**: these are *PLANNED* contact events for validation of the phase schedule. They are NOT measured/evaluated skinned-hoof physical contacts, biomechanics, leg IK, stance, or sound recordings. Downstream audio may use them as illustrative triggers only. Actual 3D evaluated hoof contact is a distinct future P0 oracle.

Human: inspect per-foot frame table. Automation: go test/run with JSON. Agent: typed, bounded inputs with failure on unsupported gait/surface/non-integral clock. No merge/release/CPE without owning DLE review.
