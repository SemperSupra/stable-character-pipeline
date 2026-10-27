# MMD W02: source-bound qualification evidence v1

**Authority:** [public DLE #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19), W02; stacked candidate branch under draft PR #20. This package is read-only research infrastructure, not a format converter, model/identity verifier, concept policy decision, runtime controller or release grant.

## Five typed primitives

1. `FixtureSpec`: original fixture identifier, rights-linked source URI, declared SHA-256 and frame count.
2. `SourceSemantics`: native PMX/VMD/VPD/glTF format, losslessly stored Japanese/Unicode bone/morph names, source unit and *nullable* unknown physical meter scale, handedness/up axis, rational frames-per-second and explicit origin, plus **asset rights distinct from engine software license**.
3. `EngineObservation`: pinned engine ID and version, exact source-digest link, frame/time, structured measured primitives, explicit declared semantic losses and PASS/FAIL/UNKNOWN/NOT_TESTED/BLOCKED.
4. `MetricEvidence`: observation-bound numerical metric, units, named independent oracle and result. Unmeasured is null, never invented zero.
5. `ProofBundle`: versioned structured evidence, verdict; a PASS is rejected unless all observations and metrics PASS with actual measurements and source cloud/redistribution permission.

The [JSON Schema](proof-bundle.schema.json) is strict on keys/types; Go cross-record validation additionally guards exact timebase, observation ancestry, metric joins, native unit/axis and premature PASS. **Neither schema validation nor Go PASS attests that a file exists, matches a declared hash, was actually run, has verified third-party rights, or is scientifically correct.** The canonical source hash must be separately independently computed from actual bytes. Those facts require per-engine independent run receipts.

## Three audiences / reproducibility

- Human: inspect [readable sample](testdata/synthetic-proof.json), labels, declared losses and failure diagnosis.
- Automation/operator: run `cd mmd/roadmap && go test -count=1 ./... && go vet ./... && go run ./cmd/envelopecheck envelope/testdata/synthetic-proof.json`. Invalid envelopes exit **4**, never exit 0.
- Agent/developer: same strict JSON input/output through `envelopecheck <path>` or stdin `-`; no hidden state, no new authority, no source write on validation.

Provenance: synthetically constructed in this W02 branch. The test digest denotes the literal bytes `original synthetic japanese rig`, **not** a real PMX file, Blake3 proof, legal approval or Blender measurement. Values are deliberately didactic fixtures; no actual engine observation is represented by this sample. Tests only qualify contract invariants, not motion. An actual engine adapter must replace synthetic fixture IDs with genuine source byte hashes, pin engine versions, record native per-frame measurements and independent source rights.

## Negative controls and limits

Unit/frame-origin/timebase missing, Unicode native-label duplicates, mismatched fixture SHA, nonfinite quantities, unknown verdict, phantom metric observation, missing metric/oracle, undeclared loss, unknown/insufficient rights, premature unknown→PASS, trailing JSON and unknown key are rejected. JSON Schema has no cross-record oracle; Go is authoritative for these structural interdependencies. No glTF/PMX parser replacement and no external provenance/rights attestation.

$0 public CPU only, synthetic material, no private people or vendor model import, no merge/release/deploy/policy promotion without independent owner gates. This W02 branch remains a review candidate; only independent exact-head GitHub Actions can qualify its Go runtime and source readback.

**W02 red-team correction:** Native source units can use `meters_per_unit:null` without inventing a physical conversion. Metric units require an explicitly declared positive scale. `EngineObservation` includes `evidence_uri` and `evidence_sha256` to bind receipt bytes; these strings still need independent byte validation. Previous golden fixture meters-per-unit was didactic and is now explicitly `null`.
