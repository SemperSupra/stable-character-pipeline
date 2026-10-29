# Stable Character provider capability gates — research contract

**Owning DLE:** [public MMD #19](https://github.com/SemperSupra/stable-character-pipeline/issues/19), pre-registered [6507536100](https://github.com/SemperSupra/stable-character-pipeline/issues/19#issuecomment-6507536100). Child of anonymous discovery [draft PR #116](https://github.com/SemperSupra/stable-character-pipeline/pull/116). Public-safe source only. **No real OAuth tokens, accounts, API keys, file downloads/uploads, private CPE queries or third-party model files.**

## Operations and coverage

`providers.v1.json` is a **documentation snapshot**, not runtime/API qualification and not a source of truth for rights. 22 providers × six distinct operations:
`search`, `download`, `upload`, `storage`, `online_edit`, `viewer`.

Every operation states its **API** and separate **website** status. The API states are `public` (credential-free documented), `gated` (authenticated endpoint documented), `conditional` (resource/plan-specific), `enterprise` (paid entitlement), `not_documented` (API unverified despite website operation), `not_offered`. Site state `yes` never implies programmable API support. Provider notes and documentation URLs support audits but are not accepted rights decisions.

`gates.Evaluate` is an **offline-only** non-actuating deterministic gate returning `READY_CANDIDATE`, `AUTH_REQUIRED`, `SCOPE_REQUIRED`, `ENTITLEMENT_REQUIRED`, `RIGHTS_UNKNOWN`, `OWNER_APPROVAL_REQUIRED`, `UNDOCUMENTED_API`, `UNAVAILABLE`, `NO_PROVIDER`, or `UNKNOWN_OPERATION`. A `READY_CANDIDATE` is **not access or license approval**: actual provider session, entitlement, item permission, token scope, target URL, cost, source custody and human confirmation remain untested. Access token ownership is a fact separate from asset rights. It does not make network requests or exchange/store tokens.

CLI for *synthetic* dry run:
```sh
cd research/providers
go test -race -count=1 ./...
go vet ./...
go run ./cmd/gated-operations | head -50
go run ./cmd/gated-operations -provider sketchfab -operation download
go run ./cmd/gated-operations -provider polycam -operation download -credential-observed -scope-verified
go run ./cmd/gated-operations -provider polyhaven -operation download -rights-verified -owner-approved
```
`--rights-verified`, `--credential-observed`, `--scope-verified`, and `--owner-approved` are **synthetic test flags**, *never proof* of an actual signed credential, authorization, or provider permission. Production adapter must replace them with independently validated signed receipts, never trust flags from untrusted callers.

## Work plan and dependencies

**Parallel stage 1:**
- A / provider-native discovery: public API and documented account-scope search, tags, facets, filenames, languages, formats. Keep source-native labels as retrieval observations, not CPE concept assertions.
- B / gated authorization: external browser OAuth 2.0 authorization-code + PKCE where supported; device approval for CLI only if provider offers it; service API key/PAT injection through trusted secret broker, no public GHA secrets; account subject, scope, rate limit, tier, expiry, revocation and per-operation challenge. Browser sessions are *not* equivalent to general API tokens.
- C / data plane and rights: per-asset author/license/redistribution/commercial/training rights and permission evidence separate from identity, entitlement and source permissions. Scoped staging, SHA256, malware/archive/dependency inspection before Blender/MMD/VRM/FBX/glTF import.
- D / human-automation-agent UI: shared state (provider, credential status, missing scopes, license hold, per-operation evidence), accessible browser controls for connection/consent and credential revocation, CLI `--json` control, discoverable agent function schema. All denied states must be observable, no silent fallback.

**Sequential joins:** provider doc capability -> real account/consent broker (private trusted executor) -> exact file rights -> operator-approved download/import -> independent file safety and native Blender/MMD QA -> scene ingest and review. SearXNG returns candidate URLs and provider lineage, never signed download tokens; CPE accepted projection comes from owner authority; don't serialize protected CPE meanings into public runner queries. Feedback stays `ConceptDiscoveryProposal`, not semantic promotion.

**Security and audit:** OAuth state+PKCE and registered redirect URI, least privilege, encrypted credential custody, scoped delegation for human/automation/agents, token refresh/revocation, no logs of secrets/refresh tokens/signed URLs, hostname binding and redirect/SSRF prevention, retries respecting 429, encrypted storage, bounded rate/cost budgets, provenance and exact trace IDs, no user-agent spoofing or anti-bot bypass. Any destructive operation, upload/publication, purchase or charge needs separate explicit admission.

**Important provider differences**:
- Sketchfab's online editing is its website's 3D scene presentation/materials/lighting tool, not verified arbitrary mesh-geometry authoring via Data API.
- BlenderKit editing is performed via Blender add-on, not a cloud browser 3D mesh editing API.
- VRoid Studio creates/edits; VRoid Hub hosts and serves allowed VRM avatars via OAuth. Don't conflate studio and hub.
- Fab marketplace buyer/seller features do not imply an officially supported general-purpose public REST API.
- Polycam Content Management API is Enterprise, authenticated and workspace-scoped, not $0 default.
- Open3DLab browser Anubis and Poly Pizza runner HTTP403 remain access holds; don't work around them.
- Google Drive is a storage/metadata service, not a native rigging editor.

Owner keeps merge, release, deploy, CPE acceptance and private character gates on HOLD.