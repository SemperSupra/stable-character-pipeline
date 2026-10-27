# W1: synthetic ASF/AMC source observation + group leakage falsifier

This Go stdlib workcell is a **source-only W1 readiness experiment** under [public motion DLE #29](https://github.com/SemperSupra/stable-character-pipeline/issues/29), stacked on unmerged shared synthetic learner PR #24. It does not download, ingest, normalize or admit any original CMU/horse data, execute Kaggle, create trainable weights, or establish original contact/kinematics. The synthetic source files each carry an explicit marker; absent this marker the parser fails closed.

## Observed primitives, not assumptions

- Acclaim ASF sections `:units`, `:root`, `:bonedata`, `:hierarchy`; bone names and DOF channel arrays; parent hierarchy with cycle and duplicate checks.
- AMC explicit `:fully-specified` and `:degrees`, monotonic consecutive source frame indices, observed channels of correct width, no missing or duplicated bone frames, finite measurements.
- CMU's own [ASF/AMC measurement guidance](https://mocap.cs.cmu.edu/info.php) states the original CMU ASF header `length 0.45` and conversion `1/0.45 × 0.0254` for stored bone lengths/root positions. This implementation **only** recognizes `length 0.45`; other values are held, not guessed or silently converted.
- `RootMeters` is root translation channel after that *declared CMU-specific* conversion. This does **not** solve ASF bone-local axes, Euler order, skeletal forward kinematics, contact, or global ground alignment.
- AMC contains no independently attested FPS/timestamps in these fixtures. Frame **indices** are observed, frame **times** are UNKNOWN. Do not use CMU's Vicon nominal 120Hz as a per-file independent timestamp claim.
- No attribution, identity, ethnicity, animal species, body geometry or time-varying appearance is inferred from source channel names. Fields describing observed 3D joints, gait or contact are explicitly UNKNOWN.
- Each admission receipt includes actual fixture SHA256 and `NOT_ADMITTED` even after this metadata gate passes. Data rights, native source bytes, external author terms and Kaggle allowlist are separate authority gates.

### Three audiences: same receipt

Humans inspect a readable JSON proof in the public Actions artifact; automation can run `go test -race -count=1 ./... && go vet ./... && go run ./cmd/admit -asf testdata/leg.synthetic.asf -amc testdata/leg.synthetic.amc -source-id synthetic/leg-v1 -capture-group synthetic/session-1 -out /tmp/new-receipt.json` in `motion_learning/asfamc`; agents consume the exact same JSON (no new shadow state or private backchannel). Output uses O_EXCL and does not overwrite results.

The `CheckSplit` primitive refuses group crossover, derivative-family crossover, duplicate ID and unknown split. The **CMU pair 18_01 and 19_01** must be one capture/interaction family if admitted; renaming derived poses, alternate camera videos, or mirrored/retargeted sequences must not permit leakage. This checks *declared* group IDs, not proof that a dishonest user hasn't lied about related source ancestry.

### Limits / independent review gates

The parser is a **strict qualification subset**, not a general ASF/AMC replacement or FK solver. Full ASF has `limits`, motion compression, angles/axis, variations of root and optional channels; support for such records requires actual source parsing and tested upstream conversion. Prefer upstream CMU code/GMOV for independent first-principles FK validation before implementing skeletal mathematics.

Native source files `02.asf / 02_01.amc` are separately named for eventual admission; `18_01/19_01` original capture filenames remain unverified. No real CMU/horse files may be substituted until per-file URL, terms, capture group, hash, coordinate frames, and authorized actuation are verified.

The separate [public $0 Go qualification workflow](../../.github/workflows/motion-asfamc-admission.yml) publishes only JSON receipt + source digests from **self-authored** fixtures, never real character data. Source-level guard failures belong in #29 and private human R012 #35; fauna ownership stays in #5.
