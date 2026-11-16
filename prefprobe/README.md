# R037 synthetic preference DOE — narrow source-safe consumer workcell

Canonical human preference authority: [private R016 #145](https://github.com/SemperSupra/stable-character-pipeline-private/issues/145). R037 photorealism DOE authority: [private #176](https://github.com/SemperSupra/stable-character-pipeline-private/issues/176). This code **does not** implement a new owner-preference database, second scheduler, gallery server, or canonical CharacterPack selection.

## Purpose and strictly limited interpretation

The workcell generates 12 invented A/B decisions on an original synthetic material scene. The synthetic “respondent” prefers matte, whereas a fixed heuristic comparator prefers glossy. Positions are reversed in alternating examples. A regularized online pairwise Bradley–Terry score updates only from the 12 synthetic training choices. Four separate original synthetic holdout events are scored without being ingested. This is a bounded algorithm/interface sanity check, NOT representative statistical evidence of improved real human preference predictions, photorealism, identity, anatomy, or aesthetic quality.

Every input FeedbackV1 must include synthetic_only=true and authority=SYNTHETIC_FIXTURE_NOT_OWNER. Real owner data is deliberately rejected by this public tool. Identity binding includes source SHA, project/character/shot scope, character ID and exact candidate IDs. TIE/NEITHER/UNSURE abstain rather than create a positive vote. Idempotency by event ID rejects contradictory feedback and duplicate counts. Context uncertainty abstains; NO canonical promotion API exists. CPE/owner validation is an external, private authority.

## Scope safety and negative controls

Strict JSON (unknown/duplicate keys, trailing bytes), inconsistent rights/schema, forged real owner feedback, bad hashes, duplicate reasons, cross-character and cross-scene leakage, repeated/synthetic reversal controls. Outputs are tagged PASS_SYNTHETIC_RANKING_CONTRACT_ONLY and NOT_OWNER_FEEDBACK_OR_REAL_PHOTOREALISM_EVIDENCE. Independent source hashes and actual consumer-authenticated decisions remain to be integrated after P0 source/semantic admission #167.

## Reproduction

    cd prefprobe
    go vet ./...
    go test -race -count=1 -v ./...
    go run . -synthetic

The public GitHub Actions workflow is .github/workflows/r037-prefprobe.yml. It uses standard free public Ubuntu only, read-only GitHub checkout and a short disposable job; it publishes only a tiny synthetic JSON result plus SHA256.

## Integration target

The existing R032 gallery #163 supplies actual immutable source-hashed render/video/model pairs. The existing R016 #145 owns explicit owner feedback, scope, revocation and human command. An admissible adapter can translate verified feedback events to private model training after P0 #167, using a gated interpreter rather than this public synthetic-only fixture. User-facing selections should support keyboard/screen readers and EN/DE/TH with semantic equivalence; real preferences are not inferred from assistant plans or synthetic data.
