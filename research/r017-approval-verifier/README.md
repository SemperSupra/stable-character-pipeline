# R017 — signed human selection *review* verifier (synthetic research)

Authority: private product DLE #2, owner D1–D4; R016 #145 preference learning is not canonicalization authority. Existing private draft #148 only defines fail-closed preflight; this separate workcell does not modify that PR, or R009 #24, R014 or R015.

- Go stdlib Ed25519 with purpose-specific domain-separated deterministic signed JSON.
- Binds issuer, candidate ID, CharacterPack revision, exact evidence SHA-256, action scope, nonce and validity window.
- External trust public keys and trusted clock; explicitly absent replay or revocation store -> UNKNOWN.
- Failure cases for signature mutation, cross-candidate, cross-revision, cross-evidence, scope escalation, expiry, revoked and replayed nonce.
- Success result is `VERIFIED_FOR_HUMAN_REVIEW_ONLY`, **never canonicalization approval, CharacterPack mutation, automatic commit or release**.
- Test-only deterministic signing key is public and must never be reused in real deployment.
- The verifier merely reads nonces: **race-safe transactional consumption is NOT implemented**, and the test key is not authenticated to the human owner. Product authority must own external IdP/key admission, key rotation, nonce transactional CAS, revocation and audit trail.
- No production protected data, vendor media, 3D model/character, private feedback or credentials in public repository/runners.

Local disposable Go stdlib tests: 18/18 synthetic cases PASS with race detector and vet. Local exact research source SHA-256 (before GitHub stage):
`verifier.go bdb131790ade56b21c658b90b30ca8219b4db291e9d7c6a5c732add38ec500b1`
`verifier_test.go 3dcec33acb099fde0d182a70f53797d2417cc974e570d4f613c0c395fdcd0b3d`.

CI is a narrow, read-only, 8-minute public GitHub Actions job with no third-party Actions and no persistent state. Observe exact GitHub run before claiming cloud qualification. No integration/merge/release/deploy/CPE promotion without review.
## Independent red/blue correction (2026-11-13)

- FIRST RED reproduced in local disposable Go: original source accepted a validly signed receipt whose caller-controlled `Scope` and expected scope were both `canonical-write`, returning `VERIFIED_FOR_HUMAN_REVIEW_ONLY`; this was an authorization-context confusion even though no actual canonical write existed.
- BLUE: explicit `candidate-review` scope is now the only admissible review verifier request. An independent `adversarial_test.go` locks the denial, with one additional transparent test documenting that two calls against the same unchanged nonce snapshot BOTH return review-verified. **Atomic single-use nonce consumption remains NOT IMPLEMENTED** and must be enforced by product authority.
- Local corrected source Go race/vet PASS (18 existing cases + 2 adversarial cases). Exact-head public GHA remains unverified until an observed completed run and logs. This is synthetic review intent only, never proof of owner authentication, actual CharacterPack canonicalization or release.
