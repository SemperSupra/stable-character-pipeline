# R10 — Public synthetic job durable replay and writer boundary

**Scope:** child of public draft R9 #215 at original source HEAD `0c65496e59e16d32e120b63b4659845018f5ea58`. R10 is public-original synthetic only; no protected R009 mesh, subject/source, Drive identifier, credential, sovereign runner, or rights authority.

## Contract and failure state

- The same immutable 40-hex source revision, job, two camera names, self-authored rights and scientific `FAIL_ABSTRACT_LIMBS_ONLY` / `UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM` / release `HELD_R009_NOT_RUN_NOT_ADMITTED` are required.
- On cold start, enumerate only `attempt-0001` etc. A historical failed attempt without `result.json` remains untouched, not success.
- A completed result is reusable **only after** the existing R9 verifier re-hashes the original source JSON, GLB, blend and both H264 byte streams and validates the complete immutable semantic receipt.
- Any nonregular attempt, partial/corrupted receipt, stale wrong source, duplicate complete result, or symlink refuses admission. No prior result is silently purged.
- A dedicated `.r10-writer.lock` directory provides an atomic filesystem exclusion across distinct local manager instances and host processes **sharing the same trusted POSIX filesystem**. Contention returns `ROOT_WRITER_BUSY_OR_RECOVERY_REQUIRED` rather than starting a duplicate native Blender job. A crashed writer deliberately leaves this lock in place; only separately admitted operator inspection may remove it after reviewing the original first-failure attempts. No automatic stale-lease stealing.
- Existing in-process mutex remains; future callers may retry a busy request and independently verify the completed immutable result. This is at-most-one *active* render writer per output root, not distributed multi-host consensus.
- No attempt to relabel scientific FAIL/UNKNOWN, add private jobs, or promote / publish / deploy this public draft.

## Qualification

`cd scenejob && go test -race -count=1 ./... && go vet ./...`.

New adversarial tests cover cold process re-creation, media GET source replay, two independent manager instances racing over one output root, forged durable originals, wrong revision, retained historical failed first attempt and retry, orphan writer lock, malformed receipt and symlinked attempt. Existing R9 native two-transport smoke remains the actual Blender/H264 parent test; source-only tests alone are not a real original Blender requalification.

## Production hardening still held

Crash recovery is operator-mediated; safe recovery of a previously abandoned running image, durable append-only attempt journal with authenticated issuer, cross-machine leases, signed original package provenance, real browser automation and production rolling upgrade are NOT implemented or admitted here. Release, deployment, CPE promotion, private actors and source rights stay HELD.
