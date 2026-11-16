# Anatomy donor source metadata preflight — R036 A1

Read-only, **public source-text-only** scan. Does not clone or download donor models, anatomy meshes, patient data, weights, build dependencies or third-party assets. Resolves each named public repository branch to an observed full commit SHA, retrieves only a README and the root license text from that immutable SHA, and outputs SHA-256 checksums, byte sizes and failures as JSON. No raw external text is committed or rehosted.

Preflight is a *provenance/operability check*, **not** legal clearance, model qualification, scientific acceptance, or approval to redistribute. Each donor asset, models submodule, weight and dependency will require its own admission.

Reproduce: `GOTOOLCHAIN=local GOPROXY=off go test -count=1 ./...`, `go vet ./...`, and `go run ./cmd/preflight`. Online probe explicitly accesses only GitHub public git HTTPS and raw README/license URLs, no API token, private data, credentials or third-party binaries. Read-only standard public GHA CPU, 5-minute job cap. Fail/UNKNOWN if any source cannot be uniquely resolved or text fetched. This is NOT yet running the actual donor engines.

Investigated sources: OpenSim, MyoSim, SOFA, ArtiSynth, FEBio and Z-Anatomy. BodyParts3D/HuBMAP are separate official dataset/API admission lanes. Rights for SOFA apps/plugins, FEBio binaries, and individual Z-Anatomy parts are **not implied by a root license**.
