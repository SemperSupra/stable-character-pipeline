# OCI deployment source-safe smoke (draft, no registry publication)

This is the **first CPU-only package and dry-run install** of the public `scenecontract` reference, not the R009 Blender product, protected-character runner, source admission, or accepted 72f human animation.

- Input exact source: scenecontract [DRAFT #207](https://github.com/SemperSupra/stable-character-pipeline/pull/207) original source-tested HEAD `4470adb9ce7bc6d656385b9064396f885db6d47f`. No private person data or protected model bytes.
- `FROM scratch` requires no package repository or base-image download during OCI build. Static Go binary built in the standard public GHA job. Nonroot UID/GID 65532, readonly root FS, no network, dropped caps, no-new-privileges, bounded CPU/PIDs/memory. Local test fixture is original fictional metadata/dummy SHA only.
- The PR GHA must run `go test -race`/vet, build binary, construct OCI image locally and **actually run** the container in restricted mode for positive structural CLI and negative missing-file exits. `docker image inspect` records a local image identifier, **NOT** a signed distribution digest or proof of binary reproducibility.
- The same Go package's HTTP and accessibility endpoints were separately tested in #207's pure Go handler tests; production HTTP server, auth, external exposure, interactive render jobs, OCI registry push, remote host/TrueNAS deploy, private source mounts and rollback remain deliberately OUT OF SCOPE / held.
- No `docker push`, no registry token, private GHA, paid runners or asset uploads. Next release ladder: signed digest/SBOM + independent scrutiny, then *owner-gated* protected actual R009 validation. Every FAIL or UNKNOWN stays open, and no merged public `main` integration exists until owner approval.
