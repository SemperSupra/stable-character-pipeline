# Source-safe release candidate gate (research, draft)

This original standard-library Go validator is a **source-only release qualification primitive**, not approval to merge, publish protected person/character content, or release the actual R009 product. Public CI must use **only** public/self-authored synthetic manifest fixtures. Protected-product manifests and artifacts must be evaluated in a separately admitted private trust zone.

Run: `cd releasegate && go test ./... && go vet ./... && go run ./cmd/releasegate sample.synthetic.json`.

`scp.release-manifest.v1` requires source commit SHA, phase (`draft`, `candidate`, `released`), scope (`public-synthetic` or `protected-product`), optional image digest in draft and mandatory image digest for candidate/released, and these 9 gates: build, contract, source_motion, render, behavior, audiences, security, custody, deployment. PASS requires a full SHA-256 receipt. For candidate and released phases, **every** gate must be PASS with valid receipt. A draft is always UNKNOWN even if all evidence appears PASS. No scientific equivalence, rights admission or authenticity can be inferred solely from this JSON.

Strict parser rejects duplicate keys, trailing JSON, unknown fields and over-1MiB input. The receipt is a pointer/digest **only**, not a proof of independent scientific validity or authorization. Threat boundary: caller supplies manifest; an independent issuer and rights/signature admission remain mandatory before any actual promotion. No private host paths or media bytes belong in public fixtures. Existing public release #1 and private R009 #23 owner holds remain.
