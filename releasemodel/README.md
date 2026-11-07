# R0c — executable bounded release-state verification (DRAFT)

This original source-safe Go state model imports **actual** R0 structural validation and R0b independent signature verification. It does not invent a separate release-state implementation to compare against itself.

The test enumerates every assignment of PASS, FAIL or UNKNOWN to the nine release gates: **3^9 = 19,683** combinations. Each is exercised in **draft, candidate and released** phases, **59,049 exact-code observations**. Only two purely structural cases can return R0 PASS (all nine PASS in candidate or released phases); 19,683 draft cases must remain UNKNOWN and 39,364 other cases fail. These **two** structurally accepted cases have *fictional receipts* and are NOT cryptographically qualified; R0b rejects them absent authentic issuers and original evidence bytes. Additional exhaustive 32 permutations of five caller owner-gate indicators prove a missing flag cannot be considered complete.

`OwnerState` flags are **model parameters**, never authenticated owner grants, signatures or production policy; even a fully green state can produce no more than `READY_FOR_MANUAL_REVIEW_NOT_RELEASED`. This component never merges, publishes, starts real R009, accesses protected character assets or deploys any image.

**Limitations:** this is bounded explicit-state executable testing, not a temporal TLA+/TLC formal proof, product human-behavior acceptance, private source entitlement, authenticated release approval or evidence that owner/private runner authorization exists. Always rerun against the exact combined candidate SHA rather than assuming individually tested draft PR heads imply integrated acceptance.

Run `cd releasemodel && go test -race -v -count=1 ./... && go vet ./...`. Public standard GHA only, no private minutes or paid runners. Authority: public release #1, private R009 #23, existing R007 canonical contract and all holds.
